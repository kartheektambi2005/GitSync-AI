"""
config_manager.py
Defines the persistent configuration schema (via pydantic) and handles
loading/saving configuration to disk in JSON or YAML format. Thread-safe
for concurrent read/write from watcher callbacks.

Config file stores:
    - list of watched folders
    - folder -> repository (GitHub URL) mappings
    - per-folder settings (branch, debounce override, auto push)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from settings import settings

_lock = threading.RLock()


class FolderMapping(BaseModel):
    """Represents a single local-folder <-> GitHub-repo mapping."""

    folder_path: str
    remote_url: str
    branch: str = settings.DEFAULT_BRANCH
    project_type: str = "unknown"
    auto_push: bool = True
    debounce_seconds: float = settings.DEBOUNCE_SECONDS
    last_synced_commit: Optional[str] = None

    @field_validator("folder_path")
    @classmethod
    def _normalize_path(cls, v: str) -> str:
        return str(Path(v).expanduser().resolve())


class AgentConfig(BaseModel):
    """Top-level persistent configuration."""

    mappings: Dict[str, FolderMapping] = Field(default_factory=dict)
    watched_folders: List[str] = Field(default_factory=list)

    def get_mapping(self, folder_path: str) -> Optional[FolderMapping]:
        key = str(Path(folder_path).expanduser().resolve())
        return self.mappings.get(key)

    def upsert_mapping(self, mapping: FolderMapping) -> None:
        self.mappings[mapping.folder_path] = mapping
        if mapping.folder_path not in self.watched_folders:
            self.watched_folders.append(mapping.folder_path)


class ConfigManager:
    """Handles reading and writing AgentConfig to disk (JSON or YAML)."""

    def __init__(self, config_dir: Optional[Path] = None, fmt: Optional[str] = None):
        self.config_dir = config_dir or settings.CONFIG_DIR
        self.fmt = (fmt or settings.CONFIG_FORMAT).lower()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        ext = "yaml" if self.fmt == "yaml" else "json"
        self.config_path = self.config_dir / f"config.{ext}"
        self._config: Optional[AgentConfig] = None

    # -- Public API -------------------------------------------------
    def load(self) -> AgentConfig:
        with _lock:
            if not self.config_path.exists():
                self._config = AgentConfig()
                self.save(self._config)
                return self._config

            raw_text = self.config_path.read_text(encoding="utf-8") or ""
            if not raw_text.strip():
                data = {}
            elif self.fmt == "yaml":
                data = yaml.safe_load(raw_text) or {}
            else:
                data = json.loads(raw_text)

            self._config = AgentConfig.model_validate(data)
            return self._config

    def save(self, config: Optional[AgentConfig] = None) -> None:
        with _lock:
            cfg = config or self._config or AgentConfig()
            self._config = cfg
            data = cfg.model_dump()
            if self.fmt == "yaml":
                text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
            else:
                text = json.dumps(data, indent=2, ensure_ascii=False)
            tmp_path = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
            tmp_path.write_text(text, encoding="utf-8")
            tmp_path.replace(self.config_path)

    @property
    def config(self) -> AgentConfig:
        if self._config is None:
            return self.load()
        return self._config

    def update_mapping(self, mapping: FolderMapping) -> None:
        with _lock:
            cfg = self.config
            cfg.upsert_mapping(mapping)
            self.save(cfg)
