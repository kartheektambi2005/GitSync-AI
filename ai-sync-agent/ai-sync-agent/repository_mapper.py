"""
repository_mapper.py
Ensures every watched folder has a known GitHub remote mapping. If a
folder has no remote configured, the user is asked once (interactively)
and the mapping is persisted so the question never repeats.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from config_manager import AgentConfig, ConfigManager, FolderMapping
from logger_manager import get_logger
from settings import settings

log = get_logger("repository_mapper")

_GITHUB_URL_RE = re.compile(
    r"^(https://github\.com/[\w.\-]+/[\w.\-]+(\.git)?|git@github\.com:[\w.\-]+/[\w.\-]+(\.git)?)$"
)


def is_valid_github_url(url: str) -> bool:
    return bool(_GITHUB_URL_RE.match(url.strip()))


class RepositoryMapper:
    """Resolves and persists folder <-> repository mappings."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def get_mapping(self, folder_path: str) -> Optional[FolderMapping]:
        return self.config_manager.config.get_mapping(folder_path)

    def ensure_mapping(
        self,
        folder_path: str,
        project_type: str = "unknown",
        prompt_fn=input,
    ) -> FolderMapping:
        """Return an existing mapping, or create one by asking the user once."""
        folder_path = str(Path(folder_path).expanduser().resolve())
        existing = self.get_mapping(folder_path)
        if existing is not None:
            if existing.project_type == "unknown" and project_type != "unknown":
                existing.project_type = project_type
                self.config_manager.update_mapping(existing)
            return existing

        log.info(f"No repository mapping found for '{folder_path}'. Prompting user.")
        remote_url = self._prompt_for_remote(folder_path, prompt_fn)

        mapping = FolderMapping(
            folder_path=folder_path,
            remote_url=remote_url,
            branch=settings.DEFAULT_BRANCH,
            project_type=project_type,
            auto_push=settings.AUTO_PUSH,
            debounce_seconds=settings.DEBOUNCE_SECONDS,
        )
        self.config_manager.update_mapping(mapping)
        log.info(f"Saved mapping: '{folder_path}' -> '{remote_url}'")
        return mapping

    @staticmethod
    def _prompt_for_remote(folder_path: str, prompt_fn) -> str:
        while True:
            url = prompt_fn(
                f"\n[SETUP] No GitHub remote configured for:\n  {folder_path}\n"
                f"Enter the GitHub repository URL "
                f"(e.g. https://github.com/user/repo.git): "
            ).strip()
            if is_valid_github_url(url):
                return url
            print("  Invalid GitHub URL. Please try again (https or git@ format).")
