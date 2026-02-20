"""Atlas configuration — spoke registry, LLM backends, encryption."""

from __future__ import annotations

import os
import secrets
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
}

# ---------------------------------------------------------------------------
# LLM backend profiles (local vLLM)
# ---------------------------------------------------------------------------

class LLMProfile:
    def __init__(self, name: str, base_url: str, model: str, max_tokens: int = 4096, temperature: float = 0.3):
        self.name = name
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature


LLM_PROFILES: dict[str, LLMProfile] = {
    "fast": LLMProfile(
        name="atlas-fast",
        base_url="http://localhost:8100/v1",
        model="Qwen/Qwen2.5-7B-Instruct",
    ),
    "quality": LLMProfile(
        name="atlas-quality",
        base_url="http://localhost:8101/v1",
        model="Qwen/Qwen2.5-72B-Instruct-AWQ",
        max_tokens=4096,
        temperature=0.2,
    ),
    "code": LLMProfile(
        name="atlas-code",
        base_url="http://localhost:8102/v1",
        model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    ),
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
# App settings
# ---------------------------------------------------------------------------

ATLAS_HOST = os.getenv("ATLAS_HOST", "0.0.0.0")
ATLAS_PORT = int(os.getenv("ATLAS_PORT", "8888"))
HEALTH_POLL_INTERVAL = 30  # seconds
SPOKE_REQUEST_TIMEOUT = 30.0  # seconds for proxied requests
