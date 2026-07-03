"""
settings.py
Global application settings loaded from environment variables (.env) with
sane defaults. Central place for all path/config constants used across
the agent.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file (if present) before anything else reads os.environ
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


class Settings:
    """Container for all runtime configuration values."""

    # --- Directories -------------------------------------------------
    BASE_DIR: Path = BASE_DIR
    CONFIG_DIR: Path = Path(os.getenv("AGENT_CONFIG_DIR", BASE_DIR / "config"))
    LOG_DIR: Path = Path(os.getenv("AGENT_LOG_DIR", BASE_DIR / "logs"))
    CACHE_DIR: Path = Path(os.getenv("AGENT_CACHE_DIR", BASE_DIR / "cache"))

    # --- Config file ---------------------------------------------------
    CONFIG_FILE_NAME: str = os.getenv("AGENT_CONFIG_FILE", "config.yaml")
    CONFIG_FORMAT: str = os.getenv("AGENT_CONFIG_FORMAT", "yaml")  # yaml | json

    # --- Watcher / debounce --------------------------------------------
    DEBOUNCE_SECONDS: float = float(os.getenv("AGENT_DEBOUNCE_SECONDS", "5"))
    IGNORED_DIR_NAMES = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".idea", ".vscode", ".pytest_cache",
        "cache", "logs", ".mypy_cache", "target", ".next",
    }
    IGNORED_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".swp", ".DS_Store"}

    # --- Git ------------------------------------------------------------
    DEFAULT_BRANCH: str = os.getenv("AGENT_DEFAULT_BRANCH", "main")
    GIT_REMOTE_NAME: str = os.getenv("AGENT_GIT_REMOTE_NAME", "origin")
    GIT_USER_NAME: str = os.getenv("GIT_USER_NAME", "")
    GIT_USER_EMAIL: str = os.getenv("GIT_USER_EMAIL", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    AUTO_PUSH: bool = _env_bool("AGENT_AUTO_PUSH", True)
    MAX_GIT_RETRIES: int = _env_int("AGENT_MAX_GIT_RETRIES", 3)
    GIT_RETRY_BACKOFF: float = float(os.getenv("AGENT_GIT_RETRY_BACKOFF", "2"))

    # --- Logging ----------------------------------------------------------
    LOG_LEVEL: str = os.getenv("AGENT_LOG_LEVEL", "INFO")
    LOG_ROTATION: str = os.getenv("AGENT_LOG_ROTATION", "5 MB")
    LOG_RETENTION: str = os.getenv("AGENT_LOG_RETENTION", "14 days")

    @classmethod
    def ensure_directories(cls) -> None:
        for d in (cls.CONFIG_DIR, cls.LOG_DIR, cls.CACHE_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
