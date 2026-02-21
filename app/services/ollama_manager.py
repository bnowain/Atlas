"""Ollama model lifecycle manager — load/unload models via Ollama HTTP API."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from enum import Enum

import httpx

from app.config import OLLAMA_MODELS, OLLAMA_BASE_URL, GPU

logger = logging.getLogger(__name__)


class ModelState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ModelStatus:
    key: str
    name: str
    model_id: str
    vram_gb: float
    context_length: int
    description: str
    default_on: bool
    state: str
    error: str | None = None
    started_at: float | None = None


@dataclass
class GPUInfo:
    name: str
    total_vram_gb: float
    used_vram_gb: float
    available_vram_gb: float
    estimated_loaded_gb: float
    models_loaded: int


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_states: dict[str, ModelState] = {}
_errors: dict[str, str | None] = {}
_started_at: dict[str, float | None] = {}
_lock = asyncio.Lock()
_health_poll_task: asyncio.Task | None = None


def _init_states():
    """Ensure every model has a default state."""
    for key in OLLAMA_MODELS:
        if key not in _states:
            _states[key] = ModelState.STOPPED
            _errors[key] = None
            _started_at[key] = None


_init_states()


# ---------------------------------------------------------------------------
# Ollama API helpers
# ---------------------------------------------------------------------------

async def _ollama_get(path: str, timeout: float = 10.0) -> dict | None:
    """GET request to Ollama API."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}{path}")
            if resp.status_code == 200:
                return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


async def _ollama_post(path: str, body: dict, timeout: float = 300.0) -> dict | None:
    """POST request to Ollama API."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}{path}", json=body)
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text}
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return {"error": str(e)}


async def _ollama_available() -> bool:
    """Check if Ollama server is reachable."""
    return await _ollama_get("/api/tags") is not None


def _model_matches(loaded_name: str, model_id: str) -> bool:
    """Check if a loaded model name matches a config model_id.

    Ollama model names can be 'qwen2.5:7b' or 'qwen2.5:7b-instruct-fp16'.
    A model_id of 'qwen2.5:7b' should match 'qwen2.5:7b' exactly,
    or the loaded name should start with the model_id.
    """
    if loaded_name == model_id:
        return True
    # Handle tag normalization: 'qwen2.5:7b' matches 'qwen2.5:7b'
    # but also 'qwen2.5:7b' could be loaded as 'qwen2.5:7b' with :latest suffix
    base = model_id.split(":")[0]
    loaded_base = loaded_name.split(":")[0]
    if base == loaded_base:
        # Same model family, check tag
        model_tag = model_id.split(":")[-1] if ":" in model_id else "latest"
        loaded_tag = loaded_name.split(":")[-1] if ":" in loaded_name else "latest"
        return model_tag == loaded_tag
    return False


async def _get_loaded_models() -> list[str]:
    """Return list of model names currently loaded in Ollama."""
    data = await _ollama_get("/api/ps")
    if data and "models" in data:
        return [m.get("model", "") or m.get("name", "") for m in data["models"]]
    return []


async def _is_model_pulled(model_id: str) -> bool:
    """Check if a model has been downloaded."""
    data = await _ollama_get("/api/tags")
    if data and "models" in data:
        for m in data["models"]:
            name = m.get("model", "") or m.get("name", "")
            if _model_matches(name, model_id):
                return True
    return False


# ---------------------------------------------------------------------------
# GPU info
# ---------------------------------------------------------------------------

async def get_gpu_info() -> GPUInfo:
    """Get GPU VRAM usage via nvidia-smi (native Windows) + Ollama ps."""
    total_gb = GPU.total_vram_gb
    used_gb = 0.0

    # nvidia-smi works natively on Windows with NVIDIA drivers
    def _query_nvidia_smi():
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                return float(parts[0].strip()) / 1024, float(parts[1].strip()) / 1024
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
            pass
        return None

    smi = await asyncio.get_event_loop().run_in_executor(None, _query_nvidia_smi)
    if smi:
        used_gb, total_gb = smi

    # Get loaded model info from Ollama ps
    models_loaded = 0
    estimated_loaded = 0.0
    ps_data = await _ollama_get("/api/ps")

    if ps_data and "models" in ps_data:
        for m in ps_data["models"]:
            models_loaded += 1
            model_name = m.get("model", "") or m.get("name", "")
            size_vram = m.get("size_vram", 0) or m.get("size", 0)
            if size_vram:
                estimated_loaded += size_vram / (1024 ** 3)
            else:
                # Fallback to config VRAM estimates
                for cfg in OLLAMA_MODELS.values():
                    if _model_matches(model_name, cfg.model_id):
                        estimated_loaded += cfg.vram_gb
                        break

    return GPUInfo(
        name=GPU.name,
        total_vram_gb=round(total_gb, 1),
        used_vram_gb=round(used_gb, 1),
        available_vram_gb=round(total_gb - used_gb, 1),
        estimated_loaded_gb=round(estimated_loaded, 1),
        models_loaded=models_loaded,
    )


# ---------------------------------------------------------------------------
# VRAM feasibility
# ---------------------------------------------------------------------------

async def check_can_load(key: str) -> tuple[bool, str]:
    """Check if there's enough VRAM to load a model."""
    model = OLLAMA_MODELS.get(key)
    if not model:
        return False, f"Unknown model: {key}"

    gpu = await get_gpu_info()
    needed = model.vram_gb
    available = gpu.available_vram_gb

    if needed > available:
        return False, (
            f"Not enough VRAM: {model.name} needs ~{needed:.1f} GB, "
            f"only {available:.1f} GB free."
        )
    return True, ""


# ---------------------------------------------------------------------------
# Start / stop models
# ---------------------------------------------------------------------------

async def start_model(key: str) -> dict:
    """Load an Ollama model into VRAM."""
    model = OLLAMA_MODELS.get(key)
    if not model:
        return {"success": False, "message": f"Unknown model: {key}", "state": "stopped"}

    async with _lock:
        state = _states.get(key, ModelState.STOPPED)
        if state in (ModelState.RUNNING, ModelState.STARTING):
            return {"success": True, "message": f"{model.name} is already {state.value}", "state": state.value}

        if not await _ollama_available():
            return {"success": False, "message": "Ollama is not running. Start it first.", "state": "stopped"}

        _states[key] = ModelState.STARTING
        _errors[key] = None

    # Load model in background
    asyncio.create_task(_load_model(key))
    return {"success": True, "message": f"Loading {model.name}...", "state": "starting"}


async def _load_model(key: str):
    """Pull (if needed) and load a model into VRAM."""
    model = OLLAMA_MODELS.get(key)
    if not model:
        return

    # Pull model if not already downloaded
    if not await _is_model_pulled(model.model_id):
        logger.info("Model %s not found locally, pulling...", model.model_id)
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Pull uses streaming NDJSON response
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"model": model.model_id, "stream": True},
                ) as resp:
                    if resp.status_code != 200:
                        async with _lock:
                            _states[key] = ModelState.ERROR
                            _errors[key] = f"Failed to pull model: HTTP {resp.status_code}"
                        return
                    async for line in resp.aiter_lines():
                        pass  # Consume stream; could parse progress later
        except Exception as e:
            async with _lock:
                _states[key] = ModelState.ERROR
                _errors[key] = f"Failed to pull model: {e}"
            return

    # Load model into VRAM: send a generate request with keep_alive=-1
    logger.info("Loading model %s into VRAM...", model.model_id)
    result = await _ollama_post("/api/generate", {
        "model": model.model_id,
        "prompt": "",
        "keep_alive": -1,  # Keep loaded indefinitely
        "stream": False,
    }, timeout=300.0)

    if result and "error" not in result:
        async with _lock:
            _states[key] = ModelState.RUNNING
            _started_at[key] = time.time()
            _errors[key] = None
        logger.info("Model %s loaded successfully", key)
    else:
        error_msg = result.get("error", "Unknown error") if result else "No response from Ollama"
        async with _lock:
            _states[key] = ModelState.ERROR
            _errors[key] = str(error_msg)
        logger.error("Failed to load model %s: %s", key, error_msg)


async def stop_model(key: str) -> dict:
    """Unload an Ollama model from VRAM."""
    model = OLLAMA_MODELS.get(key)
    if not model:
        return {"success": False, "message": f"Unknown model: {key}", "state": "stopped"}

    async with _lock:
        state = _states.get(key, ModelState.STOPPED)
        if state == ModelState.STOPPED:
            return {"success": True, "message": f"{model.name} is already stopped", "state": "stopped"}
        _states[key] = ModelState.STOPPING
        _errors[key] = None

    # Unload by setting keep_alive to 0
    await _ollama_post("/api/generate", {
        "model": model.model_id,
        "prompt": "",
        "keep_alive": 0,
        "stream": False,
    }, timeout=30.0)

    async with _lock:
        _states[key] = ModelState.STOPPED
        _started_at[key] = None

    logger.info("Model %s unloaded", key)
    return {"success": True, "message": f"{model.name} unloaded", "state": "stopped"}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

async def get_all_status() -> list[ModelStatus]:
    """Get status for all configured models."""
    return [
        ModelStatus(
            key=model.key,
            name=model.name,
            model_id=model.model_id,
            vram_gb=model.vram_gb,
            context_length=model.context_length,
            description=model.description,
            default_on=model.default_on,
            state=_states.get(key, ModelState.STOPPED).value,
            error=_errors.get(key),
            started_at=_started_at.get(key),
        )
        for key, model in OLLAMA_MODELS.items()
    ]


def get_running_profiles() -> list[str]:
    """Return keys of currently running models."""
    return [k for k, s in _states.items() if s == ModelState.RUNNING]


# ---------------------------------------------------------------------------
# Log retrieval
# ---------------------------------------------------------------------------

async def get_logs(key: str, lines: int = 50) -> str:
    """Get runtime info for a model (Ollama manages its own logs)."""
    model = OLLAMA_MODELS.get(key)
    if not model:
        return "Unknown model"

    ps_data = await _ollama_get("/api/ps")
    if ps_data and "models" in ps_data:
        for m in ps_data["models"]:
            model_name = m.get("model", "") or m.get("name", "")
            if _model_matches(model_name, model.model_id):
                return json.dumps(m, indent=2, default=str)

    state = _states.get(key, ModelState.STOPPED)
    return f"Model {model.model_id} is {state.value}. Ollama manages its own logging."


# ---------------------------------------------------------------------------
# Startup detection & defaults
# ---------------------------------------------------------------------------

async def detect_running_models():
    """On startup, check which models are already loaded in Ollama."""
    _init_states()

    if not await _ollama_available():
        logger.warning("Ollama is not running — models won't be available until it's started")
        return

    loaded = await _get_loaded_models()
    for key, model in OLLAMA_MODELS.items():
        for loaded_name in loaded:
            if _model_matches(loaded_name, model.model_id):
                _states[key] = ModelState.RUNNING
                _started_at[key] = time.time()
                logger.info("Detected running model: %s (%s)", key, model.model_id)
                break


async def startup_defaults():
    """Start default models that aren't already running."""
    for key, model in OLLAMA_MODELS.items():
        if model.default_on and _states.get(key) != ModelState.RUNNING:
            logger.info("Starting default model: %s", model.name)
            await start_model(key)


# ---------------------------------------------------------------------------
# Background health polling
# ---------------------------------------------------------------------------

async def _health_poll_loop():
    """Periodically sync state with Ollama's actual loaded models."""
    while True:
        await asyncio.sleep(15.0)
        try:
            loaded = await _get_loaded_models()
            if loaded is None:
                # Ollama unreachable — mark running models as error
                for key in OLLAMA_MODELS:
                    if _states.get(key) == ModelState.RUNNING:
                        async with _lock:
                            _states[key] = ModelState.ERROR
                            _errors[key] = "Ollama is not responding"
                continue

            for key, model in OLLAMA_MODELS.items():
                state = _states.get(key, ModelState.STOPPED)
                is_loaded = any(_model_matches(n, model.model_id) for n in loaded)

                if state == ModelState.RUNNING and not is_loaded:
                    # Model was unloaded externally (timeout, CLI, etc.)
                    async with _lock:
                        _states[key] = ModelState.STOPPED
                        _started_at[key] = None
                    logger.warning("Model %s was unloaded externally", key)

                elif state == ModelState.STOPPED and is_loaded:
                    # Model was loaded externally (via ollama CLI)
                    async with _lock:
                        _states[key] = ModelState.RUNNING
                        _started_at[key] = time.time()
                    logger.info("Model %s was loaded externally", key)

        except Exception:
            logger.exception("Error in health poll loop")


def start_health_polling():
    """Start the background health polling task."""
    global _health_poll_task
    if _health_poll_task is None or _health_poll_task.done():
        _health_poll_task = asyncio.create_task(_health_poll_loop())
        logger.info("Ollama health polling started")


def stop_health_polling():
    """Stop the background health polling task."""
    global _health_poll_task
    if _health_poll_task and not _health_poll_task.done():
        _health_poll_task.cancel()
        _health_poll_task = None
        logger.info("Ollama health polling stopped")
