"""Spoke service lifecycle manager — start, stop, health poll, auto-restart.

Mirrors the ollama_manager.py state-machine pattern but manages external
processes (spoke web servers, background workers, Docker containers).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum

import httpx

from app.config import (
    APPS_ROOT,
    SERVICE_DEFINITIONS,
    SERVICE_LOG_DIR,
    SERVICE_PID_FILE,
    ServiceDefinition,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class ServiceState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceStatus:
    key: str
    name: str
    port: int | None
    state: str
    error: str | None = None
    started_at: float | None = None
    restart_count: int = 0
    auto_start: bool = False
    process_group: str = ""
    depends_on: list[str] | None = None
    is_docker: bool = False


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_states: dict[str, ServiceState] = {}
_errors: dict[str, str | None] = {}
_pids: dict[str, int | None] = {}
_processes: dict[str, subprocess.Popen | None] = {}
_started_at: dict[str, float | None] = {}
_restart_counts: dict[str, int] = {}
_restart_timestamps: dict[str, list[float]] = {}
_spawned_by_atlas: set[str] = set()       # services WE started (vs pre-existing)
_lock = asyncio.Lock()
_health_poll_task: asyncio.Task | None = None

MAX_RESTARTS = 3
RESTART_WINDOW = 600  # 10 minutes
HEALTH_POLL_INTERVAL = 15.0
HEALTH_CHECK_TIMEOUT = 5.0
SHUTDOWN_GRACE = 5.0


def _init_states():
    """Ensure every service has a default state entry."""
    for key in SERVICE_DEFINITIONS:
        if key not in _states:
            _states[key] = ServiceState.STOPPED
            _errors[key] = None
            _pids[key] = None
            _processes[key] = None
            _started_at[key] = None
            _restart_counts[key] = 0
            _restart_timestamps[key] = []


_init_states()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_executable(svc: ServiceDefinition) -> str:
    """Return the full path to the executable for a service.

    Usually a venv Python interpreter, but can also be a venv console script
    like celery.exe — avoids the Windows problem where `python -m celery`
    spawns a child celery.exe and the parent dies, losing PID tracking.
    """
    project_dir = APPS_ROOT / svc.project_dir
    if svc.venv_relpath:
        exe_path = project_dir / svc.venv_relpath
        if exe_path.exists():
            return str(exe_path)
        logger.warning("Venv executable not found at %s, falling back to system python", exe_path)
    return sys.executable


def _health_url(svc: ServiceDefinition) -> str | None:
    """Return the full health check URL, or None if not applicable."""
    if not svc.health_path or not svc.port:
        return None
    host = "127.0.0.1"
    return f"http://{host}:{svc.port}{svc.health_path}"


def _shutdown_url(svc: ServiceDefinition) -> str | None:
    """Return the full shutdown URL, or None if not applicable."""
    if not svc.shutdown_path or not svc.port:
        return None
    host = "127.0.0.1"
    return f"http://{host}:{svc.port}{svc.shutdown_path}"


async def _check_health(url: str) -> bool:
    """Probe a health URL. Returns True if reachable and 2xx."""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            resp = await client.get(url)
            return resp.status_code < 400
    except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
        return False


def _kill_port_occupant(port: int):
    """Kill any process tree occupying a given port (Windows netstat + taskkill).

    Uses /T to kill the entire process tree — uvicorn spawns child workers
    that inherit the listening socket, so killing only the parent leaves
    children alive holding the port.
    """
    try:
        result = subprocess.run(
            ["netstat", "-aon", "-p", "TCP"],
            capture_output=True, text=True, timeout=5,
        )
        killed = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                pid = int(parts[4])
                if pid > 0 and pid not in killed:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True, timeout=5,
                    )
                    killed.add(pid)
                    logger.info("Killed orphan PID %d (tree) on port %d", pid, port)
    except Exception as e:
        logger.warning("Port cleanup failed for port %d: %s", port, e)


def _worker_cmd_signature(svc: ServiceDefinition) -> str:
    """Build a unique substring to identify this worker in process listings.

    Matches the deepest real Python process, not the venv shim.
    """
    # Use the most distinctive args (e.g. "-A app.worker.celery_app worker")
    return " ".join(svc.start_args[:3])


def _find_real_worker_pid(svc: ServiceDefinition) -> int | None:
    """Scan running processes to find the real worker PID by command line.

    On Windows, venv launchers (python.exe, celery.exe) are thin shims that
    spawn child processes and may exit. The real worker is the deepest child
    in the chain — typically C:\\Python\\Python311\\python.exe running the
    actual module code. We find it by matching command line args.
    """
    signature = _worker_cmd_signature(svc)
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"Get-CimInstance Win32_Process | "
             f"Where-Object {{ $_.CommandLine -like '*{signature}*' }} | "
             f"Select-Object ProcessId, ParentProcessId, CommandLine | "
             f"ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            return None

        import json as _json
        data = _json.loads(result.stdout)
        # PowerShell returns a single object (not array) if only one match
        if isinstance(data, dict):
            data = [data]

        # Find the deepest child: a process whose PID is NOT a parent of another
        pids = {p["ProcessId"] for p in data}
        parent_pids = {p["ParentProcessId"] for p in data}
        # Leaf processes = those whose PID is not anyone else's parent
        leaves = [p for p in data if p["ProcessId"] not in parent_pids]

        if leaves:
            # Prefer the one using the real Python (not venv shim)
            for leaf in leaves:
                cmd = leaf.get("CommandLine", "")
                if "Python3" in cmd or "Python\\Python" in cmd:
                    logger.debug("Found real worker PID %d: %s", leaf["ProcessId"], cmd[:120])
                    return leaf["ProcessId"]
            # Fallback to first leaf
            return leaves[0]["ProcessId"]

        # No leaves found, just return the first match
        return data[0]["ProcessId"] if data else None
    except Exception as e:
        logger.warning("Failed to find real worker PID: %s", e)
        return None


def _kill_worker_processes(key: str, svc: ServiceDefinition):
    """Kill all processes matching a worker's command line signature."""
    signature = _worker_cmd_signature(svc)
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"Get-CimInstance Win32_Process | "
             f"Where-Object {{ $_.CommandLine -like '*{signature}*' }} | "
             f"Select-Object ProcessId | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            return

        import json as _json
        data = _json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        for proc_info in data:
            pid = proc_info["ProcessId"]
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=5,
            )
        if data:
            logger.info("Killed %d old worker process(es) for %s", len(data), key)
    except Exception as e:
        logger.warning("Worker cleanup failed for %s: %s", key, e)


def _save_pids():
    """Persist PID map to disk for crash recovery."""
    data = {k: v for k, v in _pids.items() if v is not None}
    try:
        SERVICE_PID_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning("Failed to save PID file: %s", e)


def _load_pids() -> dict[str, int]:
    """Load PID map from disk."""
    if SERVICE_PID_FILE.exists():
        try:
            return json.loads(SERVICE_PID_FILE.read_text())
        except Exception:
            pass
    return {}


def _pid_alive(pid: int) -> bool:
    """Check if a PID is alive (Windows)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        return str(pid) in result.stdout
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Start / stop services
# ---------------------------------------------------------------------------

async def start_service(key: str) -> dict:
    """Start a service. Checks deps, spawns process, waits for health."""
    svc = SERVICE_DEFINITIONS.get(key)
    if not svc:
        return {"success": False, "message": f"Unknown service: {key}", "state": "stopped"}

    async with _lock:
        state = _states.get(key, ServiceState.STOPPED)
        if state in (ServiceState.RUNNING, ServiceState.STARTING):
            return {"success": True, "message": f"{svc.name} is already {state.value}", "state": state.value}

        # Check dependencies
        for dep_key in svc.depends_on:
            dep_state = _states.get(dep_key, ServiceState.STOPPED)
            if dep_state != ServiceState.RUNNING:
                return {
                    "success": False,
                    "message": f"Dependency '{dep_key}' is not running (state: {dep_state.value})",
                    "state": _states[key].value,
                }

        _states[key] = ServiceState.STARTING
        _errors[key] = None

    # Spawn in background task
    asyncio.create_task(_spawn_service(key))
    return {"success": True, "message": f"Starting {svc.name}...", "state": "starting"}


async def _spawn_service(key: str):
    """Actually start the process and wait for health."""
    svc = SERVICE_DEFINITIONS[key]
    project_dir = APPS_ROOT / svc.project_dir

    # Fail fast if directory doesn't exist
    if not project_dir.is_dir():
        msg = f"Project directory does not exist: {project_dir} (APPS_ROOT={APPS_ROOT})"
        async with _lock:
            _states[key] = ServiceState.ERROR
            _errors[key] = msg
        logger.error("Cannot start %s: %s", key, msg)
        return

    try:
        if svc.is_docker:
            await _start_docker_service(svc, project_dir)
        else:
            await _start_process(key, svc, project_dir)
    except Exception as e:
        async with _lock:
            _states[key] = ServiceState.ERROR
            _errors[key] = str(e)
        logger.error("Failed to start %s: %s", key, e)


async def _start_docker_service(svc: ServiceDefinition, project_dir):
    """Start a Docker Compose service."""
    def _run():
        return subprocess.run(
            ["docker", "compose", "up", "-d", svc.docker_service],
            cwd=str(project_dir),
            capture_output=True, text=True, timeout=30,
        )

    result = await asyncio.get_event_loop().run_in_executor(None, _run)
    if result.returncode != 0:
        async with _lock:
            _states[svc.key] = ServiceState.ERROR
            _errors[svc.key] = result.stderr.strip() or "Docker compose failed"
        return

    # Docker services are considered running immediately
    async with _lock:
        _states[svc.key] = ServiceState.RUNNING
        _started_at[svc.key] = time.time()
    logger.info("Docker service %s started", svc.key)


def _purge_pycache(project_dir):
    """Delete all __pycache__ dirs under the project's app/ folder.

    Prevents stale .pyc bytecode from being loaded after source edits —
    especially on Windows where mtime granularity can fool the cache.
    """
    import shutil
    app_dir = project_dir / "app"
    if not app_dir.is_dir():
        return
    count = 0
    for cache_dir in app_dir.rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir)
            count += 1
        except Exception:
            pass
    if count:
        logger.debug("Purged %d __pycache__ dirs under %s", count, app_dir)


async def _start_process(key: str, svc: ServiceDefinition, project_dir):
    """Start a Python process for a service."""
    # Purge stale bytecode cache before launching
    await asyncio.get_event_loop().run_in_executor(None, _purge_pycache, project_dir)

    # Kill any orphan — by port for web services, by command line for workers
    if svc.port:
        await asyncio.get_event_loop().run_in_executor(None, _kill_port_occupant, svc.port)
    else:
        # Workers have no port — kill by tracked PID or by command line scan
        await asyncio.get_event_loop().run_in_executor(
            None, _kill_worker_processes, key, svc,
        )

    exe = _resolve_executable(svc)
    cmd = [exe] + svc.start_args

    log_file = SERVICE_LOG_DIR / f"{key}.log"
    env = {**os.environ, "PYTHONPATH": ".", "PYTHONUNBUFFERED": "1"}

    def _spawn():
        fh = open(log_file, "a", encoding="utf-8", errors="replace")
        fh.write(f"\n--- Starting {svc.name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        fh.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_dir),
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        return proc, fh

    proc, _ = await asyncio.get_event_loop().run_in_executor(None, _spawn)

    async with _lock:
        _processes[key] = proc
        _pids[key] = proc.pid

    _save_pids()

    # Wait for health check (with port) or just check process is alive (workers)
    health_url = _health_url(svc)
    if health_url:
        healthy = False
        for _ in range(30):  # wait up to 30 seconds
            await asyncio.sleep(1)
            if proc.poll() is not None:
                # Process died
                async with _lock:
                    _states[key] = ServiceState.ERROR
                    _errors[key] = "Process exited during startup"
                    _pids[key] = None
                    _processes[key] = None
                _save_pids()
                return
            if await _check_health(health_url):
                healthy = True
                break

        if healthy:
            async with _lock:
                _states[key] = ServiceState.RUNNING
                _started_at[key] = time.time()
                _spawned_by_atlas.add(key)
            logger.info("Service %s started (PID %d, port %d)", key, proc.pid, svc.port)
        else:
            async with _lock:
                _states[key] = ServiceState.ERROR
                _errors[key] = "Health check timed out after 30s"
            logger.error("Service %s failed health check", key)
    else:
        # Background worker on Windows: the venv shim process exits quickly
        # while the real worker runs as a grandchild. Poll for the actual
        # worker PID by command line matching — workers like Celery can take
        # 30+ seconds to finish initialization before they appear stable.
        real_pid = None
        poll_interval = 3
        max_attempts = 15  # up to 45 seconds total
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            if proc.poll() is not None:
                # Shim process exited with an error — worker likely crashed
                break
            real_pid = await asyncio.get_event_loop().run_in_executor(
                None, _find_real_worker_pid, svc,
            )
            if real_pid:
                logger.debug(
                    "Service %s: found worker PID %d after %ds",
                    key, real_pid, (attempt + 1) * poll_interval,
                )
                break

        if real_pid:
            async with _lock:
                _pids[key] = real_pid
                _states[key] = ServiceState.RUNNING
                _started_at[key] = time.time()
                _spawned_by_atlas.add(key)
            _save_pids()
            logger.info("Service %s started (real PID %d, worker)", key, real_pid)
        else:
            async with _lock:
                _states[key] = ServiceState.ERROR
                _errors[key] = f"Worker process not found after {max_attempts * poll_interval}s"
                _pids[key] = None
                _processes[key] = None
            _save_pids()
            logger.error("Service %s: could not find real worker PID", key)


async def stop_service(key: str) -> dict:
    """Stop a service. Uses graceful shutdown endpoint, falls back to taskkill."""
    svc = SERVICE_DEFINITIONS.get(key)
    if not svc:
        return {"success": False, "message": f"Unknown service: {key}", "state": "stopped"}

    async with _lock:
        state = _states.get(key, ServiceState.STOPPED)
        if state == ServiceState.STOPPED:
            return {"success": True, "message": f"{svc.name} is already stopped", "state": "stopped"}
        _states[key] = ServiceState.STOPPING
        _errors[key] = None

    try:
        if svc.is_docker:
            await _stop_docker_service(svc)
        else:
            await _stop_process(key, svc)
    except Exception as e:
        logger.warning("Error stopping %s: %s", key, e)

    async with _lock:
        _states[key] = ServiceState.STOPPED
        _started_at[key] = None
        _pids[key] = None
        _processes[key] = None
        _restart_counts[key] = 0
        _spawned_by_atlas.discard(key)

    _save_pids()
    logger.info("Service %s stopped", key)
    return {"success": True, "message": f"{svc.name} stopped", "state": "stopped"}


async def _stop_docker_service(svc: ServiceDefinition):
    """Stop a Docker Compose service."""
    project_dir = APPS_ROOT / svc.project_dir

    def _run():
        return subprocess.run(
            ["docker", "compose", "stop", svc.docker_service],
            cwd=str(project_dir),
            capture_output=True, text=True, timeout=30,
        )

    await asyncio.get_event_loop().run_in_executor(None, _run)


async def _stop_process(key: str, svc: ServiceDefinition):
    """Stop a process. Try graceful shutdown, then taskkill."""
    shutdown_url = _shutdown_url(svc)

    # Try graceful shutdown via HTTP
    if shutdown_url:
        try:
            async with httpx.AsyncClient(timeout=SHUTDOWN_GRACE) as client:
                await client.post(shutdown_url)
            # Wait for process to exit
            proc = _processes.get(key)
            if proc:
                for _ in range(10):  # wait up to 5s
                    await asyncio.sleep(0.5)
                    if proc.poll() is not None:
                        return
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
            pass

    # Fallback: taskkill
    pid = _pids.get(key)
    if pid:
        def _kill():
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        await asyncio.get_event_loop().run_in_executor(None, _kill)

    # Also kill by port as extra safety
    if svc.port:
        await asyncio.get_event_loop().run_in_executor(None, _kill_port_occupant, svc.port)


async def restart_service(key: str) -> dict:
    """Stop then start a service."""
    await stop_service(key)
    await asyncio.sleep(1)
    return await start_service(key)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

async def get_all_status(auto_start_map: dict[str, bool] | None = None) -> list[ServiceStatus]:
    """Get status for all configured services."""
    if auto_start_map is None:
        auto_start_map = {}
    return [
        ServiceStatus(
            key=svc.key,
            name=svc.name,
            port=svc.port,
            state=_states.get(key, ServiceState.STOPPED).value,
            error=_errors.get(key),
            started_at=_started_at.get(key),
            restart_count=_restart_counts.get(key, 0),
            auto_start=auto_start_map.get(key, False),
            process_group=svc.process_group,
            depends_on=svc.depends_on,
            is_docker=svc.is_docker,
        )
        for key, svc in SERVICE_DEFINITIONS.items()
    ]


# ---------------------------------------------------------------------------
# Log retrieval
# ---------------------------------------------------------------------------

def get_logs(key: str, lines: int = 100) -> str:
    """Read the tail of a service's log file."""
    svc = SERVICE_DEFINITIONS.get(key)
    if not svc:
        return "Unknown service"

    log_file = SERVICE_LOG_DIR / f"{key}.log"
    if not log_file.exists():
        state = _states.get(key, ServiceState.STOPPED)
        return f"No log file yet. Service is {state.value}."

    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
        log_lines = text.splitlines()
        return "\n".join(log_lines[-lines:])
    except Exception as e:
        return f"Error reading logs: {e}"


# ---------------------------------------------------------------------------
# Startup detection
# ---------------------------------------------------------------------------

async def detect_running_services():
    """On Atlas startup, probe health endpoints to find already-running spokes."""
    _init_states()
    saved_pids = _load_pids()

    for key, svc in SERVICE_DEFINITIONS.items():
        health_url = _health_url(svc)
        if health_url and await _check_health(health_url):
            _states[key] = ServiceState.RUNNING
            _started_at[key] = time.time()
            # Restore PID if available
            if key in saved_pids:
                pid = saved_pids[key]
                if _pid_alive(pid):
                    _pids[key] = pid
            logger.info("Detected running service: %s (port %d)", key, svc.port)
        elif svc.is_docker:
            # Check if Docker service is running
            is_running = await _check_docker_running(svc)
            if is_running:
                _states[key] = ServiceState.RUNNING
                _started_at[key] = time.time()
                logger.info("Detected running Docker service: %s", key)
        elif not health_url and key in saved_pids:
            # Worker — check if saved PID is alive
            pid = saved_pids[key]
            if _pid_alive(pid):
                _states[key] = ServiceState.RUNNING
                _started_at[key] = time.time()
                _pids[key] = pid
                logger.info("Detected running worker: %s (PID %d)", key, pid)


async def _check_docker_running(svc: ServiceDefinition) -> bool:
    """Check if a Docker Compose service container is running."""
    project_dir = APPS_ROOT / svc.project_dir

    def _run():
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--status", "running", "--format", "json", svc.docker_service],
                cwd=str(project_dir),
                capture_output=True, text=True, timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ---------------------------------------------------------------------------
# Auto-start from DB settings
# ---------------------------------------------------------------------------

async def startup_auto_start_services(auto_start_keys: list[str]):
    """Start services that have auto_start enabled. Called during Atlas startup."""
    if not auto_start_keys:
        return

    logger.info("Auto-starting services: %s", auto_start_keys)

    # Sort by dependencies: start services with no deps first
    ordered = _dependency_sort(auto_start_keys)

    for key in ordered:
        state = _states.get(key, ServiceState.STOPPED)
        if state == ServiceState.RUNNING:
            continue
        logger.info("Auto-starting: %s", key)
        result = await start_service(key)
        if not result.get("success"):
            logger.warning("Auto-start failed for %s: %s", key, result.get("message"))
        else:
            # Wait for it to be running before starting dependents
            for _ in range(35):
                await asyncio.sleep(1)
                if _states.get(key) in (ServiceState.RUNNING, ServiceState.ERROR):
                    break


def _dependency_sort(keys: list[str]) -> list[str]:
    """Topological sort based on depends_on."""
    key_set = set(keys)
    result = []
    visited = set()

    def visit(k):
        if k in visited:
            return
        visited.add(k)
        svc = SERVICE_DEFINITIONS.get(k)
        if svc:
            for dep in svc.depends_on:
                if dep in key_set:
                    visit(dep)
        result.append(k)

    for k in keys:
        visit(k)
    return result


# ---------------------------------------------------------------------------
# Background health polling + auto-restart
# ---------------------------------------------------------------------------

async def _health_poll_loop():
    """Periodically check RUNNING services and auto-restart on failure."""
    while True:
        await asyncio.sleep(HEALTH_POLL_INTERVAL)
        try:
            for key, svc in SERVICE_DEFINITIONS.items():
                state = _states.get(key, ServiceState.STOPPED)
                if state != ServiceState.RUNNING:
                    continue

                # Check health
                is_healthy = True
                health_url = _health_url(svc)

                if health_url:
                    is_healthy = await _check_health(health_url)
                elif not svc.is_docker:
                    # Worker — check the real PID (which we found by scanning)
                    pid = _pids.get(key)
                    if pid:
                        is_healthy = await asyncio.get_event_loop().run_in_executor(
                            None, _pid_alive, pid
                        )
                    else:
                        # No tracked PID — try to find the real worker by cmd scan
                        real_pid = await asyncio.get_event_loop().run_in_executor(
                            None, _find_real_worker_pid, svc,
                        )
                        if real_pid:
                            async with _lock:
                                _pids[key] = real_pid
                            _save_pids()
                            is_healthy = True
                        else:
                            is_healthy = False

                if not is_healthy:
                    logger.warning("Service %s is unhealthy, attempting auto-restart", key)
                    await _auto_restart(key)

        except Exception:
            logger.exception("Error in service health poll loop")


async def _auto_restart(key: str):
    """Attempt to auto-restart a service, respecting restart limits."""
    now = time.time()

    # Clean old timestamps outside the window
    _restart_timestamps[key] = [
        ts for ts in _restart_timestamps[key] if now - ts < RESTART_WINDOW
    ]

    if len(_restart_timestamps[key]) >= MAX_RESTARTS:
        async with _lock:
            _states[key] = ServiceState.ERROR
            _errors[key] = f"Max restarts ({MAX_RESTARTS}) reached in {RESTART_WINDOW // 60}min window"
            _restart_counts[key] = MAX_RESTARTS
        logger.error("Service %s exceeded restart limit", key)
        return

    _restart_timestamps[key].append(now)

    async with _lock:
        _restart_counts[key] = len(_restart_timestamps[key])

    # Actually stop the old process (kills process tree + port cleanup)
    # before starting a new one — don't just reset state.
    await stop_service(key)

    result = await start_service(key)
    if result.get("success"):
        logger.info("Auto-restart initiated for %s", key)
    else:
        logger.error("Auto-restart failed for %s: %s", key, result.get("message"))
        async with _lock:
            _states[key] = ServiceState.ERROR
            _errors[key] = f"Auto-restart failed: {result.get('message', 'unknown')}"


def start_health_polling():
    """Start the background health polling task."""
    global _health_poll_task

    # Log path resolution for diagnostics
    logger.info("Service manager APPS_ROOT: %s (exists=%s)", APPS_ROOT, APPS_ROOT.is_dir())
    for key, svc in SERVICE_DEFINITIONS.items():
        project_dir = APPS_ROOT / svc.project_dir
        if not project_dir.is_dir():
            logger.warning("  %s: project_dir MISSING → %s", key, project_dir)

    if _health_poll_task is None or _health_poll_task.done():
        _health_poll_task = asyncio.create_task(_health_poll_loop())
        logger.info("Service health polling started")


def stop_health_polling():
    """Stop the background health polling task."""
    global _health_poll_task
    if _health_poll_task and not _health_poll_task.done():
        _health_poll_task.cancel()
        _health_poll_task = None
        logger.info("Service health polling stopped")


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

async def start_all_services() -> list[dict]:
    """Start all services in dependency order."""
    all_keys = list(SERVICE_DEFINITIONS.keys())
    ordered = _dependency_sort(all_keys)
    results = []

    for key in ordered:
        state = _states.get(key, ServiceState.STOPPED)
        if state == ServiceState.RUNNING:
            results.append({"key": key, "success": True, "message": "Already running"})
            continue
        result = await start_service(key)
        results.append({"key": key, **result})

        # Wait briefly for service to be ready before starting dependents
        if result.get("success"):
            for _ in range(35):
                await asyncio.sleep(1)
                if _states.get(key) in (ServiceState.RUNNING, ServiceState.ERROR):
                    break

    return results


async def stop_all_services() -> list[dict]:
    """Stop all running services (reverse dependency order)."""
    all_keys = list(SERVICE_DEFINITIONS.keys())
    ordered = _dependency_sort(all_keys)
    ordered.reverse()  # Stop dependents first
    results = []

    for key in ordered:
        state = _states.get(key, ServiceState.STOPPED)
        if state == ServiceState.STOPPED:
            results.append({"key": key, "success": True, "message": "Already stopped"})
            continue
        result = await stop_service(key)
        results.append({"key": key, **result})

    return results


async def stop_spawned_services():
    """Stop only services that Atlas spawned this session.

    Called on Atlas shutdown (Ctrl+C / SIGTERM). Services that were detected
    as already-running on startup are left alone — they were started
    independently and should survive Atlas restarts.
    """
    if not _spawned_by_atlas:
        logger.info("No Atlas-spawned services to stop on shutdown")
        return

    to_stop = [k for k in _spawned_by_atlas if _states.get(k) == ServiceState.RUNNING]
    if not to_stop:
        return

    ordered = _dependency_sort(to_stop)
    ordered.reverse()  # Stop dependents first

    logger.info("Stopping Atlas-spawned services: %s", ordered)
    for key in ordered:
        try:
            await stop_service(key)
        except Exception:
            logger.warning("Error stopping %s on shutdown", key, exc_info=True)
