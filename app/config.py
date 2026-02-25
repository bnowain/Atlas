"""Atlas configuration — spoke registry, LLM backends, encryption."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_DIR / 'atlas.db'}"


# ---------------------------------------------------------------------------
# Spoke registry
# ---------------------------------------------------------------------------

class SpokeConfig:
    def __init__(self, key: str, name: str, base_url: str, health_path: str, timeout: float = 10.0):
        self.key = key
        self.name = name
        self.base_url = base_url
        self.health_path = health_path
        self.timeout = timeout


SPOKES: dict[str, SpokeConfig] = {
    "civic_media": SpokeConfig(
        key="civic_media",
        name="Civic Media",
        base_url="http://localhost:8000",
        health_path="/api/health",
    ),
    "article_tracker": SpokeConfig(
        key="article_tracker",
        name="Article Tracker",
        base_url="http://localhost:5000",
        health_path="/api/stats",  # no dedicated health endpoint
    ),
    "shasta_db": SpokeConfig(
        key="shasta_db",
        name="Shasta-DB",
        base_url="http://localhost:8844",
        health_path="/health",
    ),
    "facebook_offline": SpokeConfig(
        key="facebook_offline",
        name="Facebook Offline",
        base_url="http://localhost:8147",
        health_path="/api/health",
    ),
    "shasta_pra": SpokeConfig(
        key="shasta_pra",
        name="Shasta PRA",
        base_url="http://localhost:8845",
        health_path="/api/health",
    ),
    "facebook_monitor": SpokeConfig(
        key="facebook_monitor",
        name="Facebook Monitor",
        base_url="http://localhost:8150",
        health_path="/api/health",
    ),
    "campaign_finance": SpokeConfig(
        key="campaign_finance",
        name="Campaign Finance",
        base_url="http://localhost:8855",
        health_path="/api/health",
    ),
}

# ---------------------------------------------------------------------------
# LLM backend profiles (Ollama)
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@dataclass
class OllamaModel:
    """An Ollama model that can be pulled, loaded, and unloaded."""
    key: str
    name: str
    model_id: str           # Ollama model tag, e.g. "qwen2.5:7b"
    vram_gb: float           # Approximate VRAM when loaded
    default_on: bool = False
    description: str = ""
    max_tokens: int = 4096
    temperature: float = 0.3
    context_length: int = 8192

    @property
    def base_url(self) -> str:
        return f"{OLLAMA_BASE_URL}/v1"


OLLAMA_MODELS: dict[str, OllamaModel] = {
    "fast": OllamaModel(
        key="fast",
        name="atlas-fast",
        model_id="qwen2.5:7b",
        vram_gb=5.0,
        description="Fast 7B model for quick queries",
    ),
    "quality": OllamaModel(
        key="quality",
        name="atlas-quality",
        model_id="qwen2.5:32b",
        vram_gb=20.0,
        default_on=True,
        temperature=0.2,
        description="High quality 32B model for deep analysis",
    ),
    "code": OllamaModel(
        key="code",
        name="atlas-code",
        model_id="qwen2.5-coder:7b",
        vram_gb=5.0,
        description="Code-specialized 7B model",
    ),
}


@dataclass
class GPUConfig:
    name: str = "NVIDIA RTX 5090"
    total_vram_gb: float = 32.0


GPU = GPUConfig()


# Backward-compatible LLMProfile for llm_client.py
class LLMProfile:
    def __init__(self, name: str, base_url: str, model: str, max_tokens: int = 4096, temperature: float = 0.3):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature


LLM_PROFILES: dict[str, LLMProfile] = {
    key: LLMProfile(
        name=m.name,
        base_url=m.base_url,
        model=m.model_id,
        max_tokens=m.max_tokens,
        temperature=m.temperature,
    )
    for key, m in OLLAMA_MODELS.items()
}

# Fallback chains for local profiles
LLM_FALLBACKS: dict[str, str] = {
    "quality": "fast",
    "code": "fast",
}

# ---------------------------------------------------------------------------
# Encryption key for API keys at rest
# ---------------------------------------------------------------------------

_FERNET_KEY_FILE = DATABASE_DIR / ".fernet.key"


def get_fernet_key() -> bytes:
    """Return a persistent Fernet key, creating one on first run."""
    if _FERNET_KEY_FILE.exists():
        return _FERNET_KEY_FILE.read_bytes()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    _FERNET_KEY_FILE.write_bytes(key)
    return key


# ---------------------------------------------------------------------------
# Embedding / RAG (LazyChroma)
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_VERSION = 1
CHROMA_PERSIST_DIR = DATABASE_DIR / "chroma"

# ---------------------------------------------------------------------------
# App settings
# ---------------------------------------------------------------------------

ATLAS_HOST = os.getenv("ATLAS_HOST", "0.0.0.0")
ATLAS_PORT = int(os.getenv("ATLAS_PORT", "8888"))
HEALTH_POLL_INTERVAL = 30  # seconds
SPOKE_REQUEST_TIMEOUT = 30.0  # seconds for proxied requests

# ---------------------------------------------------------------------------
# Service Manager — spoke lifecycle definitions
# ---------------------------------------------------------------------------

APPS_ROOT = Path(os.getenv("APPS_ROOT", str(BASE_DIR.parent)))
SERVICE_LOG_DIR = DATABASE_DIR / "logs"
SERVICE_LOG_DIR.mkdir(exist_ok=True)
SERVICE_PID_FILE = DATABASE_DIR / ".service_pids.json"


@dataclass
class ServiceDefinition:
    """Definition of a managed service (spoke process or background worker)."""
    key: str                            # Unique identifier, e.g. "civic_media_web"
    spoke_key: str                      # Atlas spoke key for health checks (or "")
    name: str                           # Display name
    port: int | None                    # HTTP port (None for background workers)
    project_dir: str                    # Relative to APPS_ROOT
    venv_relpath: str | None            # e.g. "venv/Scripts/python.exe", None = system python
    start_args: list[str]               # Arguments after python.exe
    health_path: str | None             # URL path for health check (None for workers)
    shutdown_path: str | None           # URL path for graceful shutdown (None for workers)
    depends_on: list[str]               # Service keys that must be running first
    is_docker: bool = False             # True for Docker-managed services
    docker_service: str = ""            # docker compose service name
    process_group: str = ""             # UI grouping label


SERVICE_DEFINITIONS: dict[str, ServiceDefinition] = {
    "civic_media_redis": ServiceDefinition(
        key="civic_media_redis",
        spoke_key="",
        name="Redis (Docker)",
        port=6379,
        project_dir="civic_media",
        venv_relpath=None,
        start_args=[],
        health_path=None,
        shutdown_path=None,
        depends_on=[],
        is_docker=True,
        docker_service="redis",
        process_group="Civic Media",
    ),
    "civic_media_web": ServiceDefinition(
        key="civic_media_web",
        spoke_key="civic_media",
        name="Civic Media API",
        port=8000,
        project_dir="civic_media",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=["civic_media_redis"],
        process_group="Civic Media",
    ),
    "civic_media_worker": ServiceDefinition(
        key="civic_media_worker",
        spoke_key="",
        name="Civic Media Worker",
        port=None,
        project_dir="civic_media",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["-m", "celery", "-A", "app.worker.celery_app", "worker",
                     "--loglevel=info", "--concurrency=1", "--pool=solo"],
        health_path=None,
        shutdown_path=None,
        depends_on=["civic_media_redis"],
        process_group="Civic Media",
    ),
    "article_tracker_web": ServiceDefinition(
        key="article_tracker_web",
        spoke_key="article_tracker",
        name="Article Tracker Web",
        port=5000,
        project_dir="article-tracker",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["web.py", "--port", "5000"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Article Tracker",
    ),
    "article_tracker_fetcher": ServiceDefinition(
        key="article_tracker_fetcher",
        spoke_key="",
        name="Article Tracker Fetcher",
        port=None,
        project_dir="article-tracker",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["run.py", "--continuous"],
        health_path=None,
        shutdown_path=None,
        depends_on=[],
        process_group="Article Tracker",
    ),
    "shasta_db": ServiceDefinition(
        key="shasta_db",
        spoke_key="shasta_db",
        name="Shasta-DB",
        port=8844,
        project_dir="Shasta-DB",
        venv_relpath=".venv/Scripts/python.exe",
        start_args=["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8844"],
        health_path="/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Shasta-DB",
    ),
    "shasta_pra": ServiceDefinition(
        key="shasta_pra",
        spoke_key="shasta_pra",
        name="Shasta PRA",
        port=8845,
        project_dir="Shasta-PRA-Backup",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8845"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Shasta PRA",
    ),
    "campaign_finance": ServiceDefinition(
        key="campaign_finance",
        spoke_key="campaign_finance",
        name="Campaign Finance",
        port=8855,
        project_dir="Shasta-Campaign-Finance",
        venv_relpath=None,
        start_args=["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8855"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Campaign Finance",
    ),
    "facebook_monitor_web": ServiceDefinition(
        key="facebook_monitor_web",
        spoke_key="facebook_monitor",
        name="FB Monitor Web",
        port=8150,
        project_dir="Facebook-Monitor",
        venv_relpath=None,
        start_args=["web_ui.py", "--port", "8150"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Facebook Monitor",
    ),
    "facebook_monitor_scraper": ServiceDefinition(
        key="facebook_monitor_scraper",
        spoke_key="",
        name="FB Monitor Scraper",
        port=None,
        project_dir="Facebook-Monitor",
        venv_relpath=None,
        start_args=["fb_monitor.py", "--watch"],
        health_path=None,
        shutdown_path=None,
        depends_on=["facebook_monitor_web"],
        process_group="Facebook Monitor",
    ),
    "facebook_offline": ServiceDefinition(
        key="facebook_offline",
        spoke_key="facebook_offline",
        name="Facebook Offline",
        port=8147,
        project_dir="Facebook-Offline/facebook-viewer/backend",
        venv_relpath="venv/Scripts/python.exe",
        start_args=["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8147"],
        health_path="/api/health",
        shutdown_path="/api/system/shutdown",
        depends_on=[],
        process_group="Facebook Offline",
    ),
}
