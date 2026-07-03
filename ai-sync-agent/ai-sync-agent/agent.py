#!/usr/bin/env python3
"""
agent.py
Main entry point for the AI Sync Agent.

Usage:
    python agent.py
    python agent.py "D:/Projects/RealEstateProject"
    python agent.py "/path/to/project1" "/path/to/project2"

The agent watches the given folder(s) (or previously-configured folders if
none are given), automatically detects project types, ensures each folder
is a Git repository mapped to a GitHub remote, and keeps the remote in
sync automatically: on file changes it debounces, stages, generates an
intelligent commit message, commits and pushes.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import List, Optional

from git.exc import GitCommandError

from commit_generator import CommitGenerator
from config_manager import ConfigManager, FolderMapping
from git_manager import GitManager
from logger_manager import get_logger
from repository_mapper import RepositoryMapper
from settings import settings
from watcher import FolderWatcher, detect_project_type

log = get_logger("agent")


class SyncAgent:
    """Top-level orchestrator wiring together watcher, git and config layers."""

    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.repo_mapper = RepositoryMapper(self.config_manager)
        self.commit_generator = CommitGenerator()
        self.watcher = FolderWatcher(on_settled=self.handle_settled_changes)
        self._git_managers: dict[str, GitManager] = {}
        self._state_file = settings.CACHE_DIR / "state.json"

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    def add_folder(self, folder_path: str) -> None:
        folder_path = str(Path(folder_path).expanduser().resolve())
        if not Path(folder_path).exists():
            log.warning(f"Folder does not exist, creating it: {folder_path}")
            Path(folder_path).mkdir(parents=True, exist_ok=True)

        project_type = detect_project_type(folder_path)
        log.info(f"Detected project type for '{folder_path}': {project_type}")

        mapping = self.repo_mapper.ensure_mapping(folder_path, project_type=project_type)

        git_manager = GitManager(folder_path)
        git_manager.detect_or_init_repo(mapping.branch)
        git_manager.ensure_remote(mapping.remote_url)
        self._git_managers[folder_path] = git_manager

        self.watcher.watch(folder_path, debounce_seconds=mapping.debounce_seconds)

    def load_configured_folders(self) -> List[str]:
        cfg = self.config_manager.load()
        return list(cfg.watched_folders)

    # ------------------------------------------------------------------
    # Change handling (called by watcher after debounce settles)
    # ------------------------------------------------------------------
    def handle_settled_changes(self, folder_path: str) -> None:
        mapping = self.repo_mapper.get_mapping(folder_path)
        git_manager = self._git_managers.get(folder_path)

        if mapping is None or git_manager is None:
            log.error(f"No mapping/git manager registered for {folder_path}; skipping sync.")
            return

        try:
            if not git_manager.has_changes():
                log.debug(f"No net changes to sync for {folder_path}.")
                return

            status = git_manager.get_status_summary()
            message = self.commit_generator.generate(status)

            git_manager.stage_all()
            sha = git_manager.commit(message)
            if sha is None:
                return

            if mapping.auto_push:
                try:
                    git_manager.push(branch=mapping.branch)
                except GitCommandError as exc:
                    log.error(f"Push failed after retries for {folder_path}: {exc}")

            mapping.last_synced_commit = sha
            self.config_manager.update_mapping(mapping)
            self._save_state(folder_path, sha)

        except Exception as exc:  # noqa: BLE001
            log.exception(f"Unexpected error syncing {folder_path}: {exc}")

    # ------------------------------------------------------------------
    # Recovery / state persistence
    # ------------------------------------------------------------------
    def _save_state(self, folder_path: str, last_commit: Optional[str]) -> None:
        state = {}
        if self._state_file.exists():
            try:
                state = json.loads(self._state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                state = {}
        state[folder_path] = {"last_commit": last_commit, "timestamp": time.time()}
        self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def recover_state(self) -> None:
        """On restart, reconcile any changes that happened while offline."""
        for folder_path in list(self._git_managers.keys()):
            git_manager = self._git_managers[folder_path]
            if git_manager.has_changes():
                log.info(f"Detected offline changes in {folder_path}; syncing now.")
                self.handle_settled_changes(folder_path)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def run(self, folders: List[str]) -> None:
        if not folders:
            folders = self.load_configured_folders()

        if not folders:
            log.error(
                "No folders configured. Provide at least one folder path, e.g.\n"
                "  python agent.py \"/path/to/project\""
            )
            sys.exit(1)

        for folder in folders:
            self.add_folder(folder)

        self.recover_state()

        self.watcher.start()
        log.info("AI Sync Agent is running. Press Ctrl+C to stop.")

        stop_event_holder = {"stop": False}

        def _signal_handler(signum, frame):  # noqa: ANN001
            log.info("Shutdown signal received. Stopping agent...")
            stop_event_holder["stop"] = True

        signal.signal(signal.SIGINT, _signal_handler)
        try:
            signal.signal(signal.SIGTERM, _signal_handler)
        except (AttributeError, ValueError):
            pass  # SIGTERM not available on some platforms

        try:
            while not stop_event_holder["stop"]:
                time.sleep(1)
        finally:
            self.watcher.stop()
            log.info("AI Sync Agent stopped cleanly.")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.py",
        description="Autonomous AI agent that watches local folders and syncs them to GitHub.",
    )
    parser.add_argument(
        "folders",
        nargs="*",
        help="One or more local project folders to watch. "
        "If omitted, previously configured folders are used.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    agent = SyncAgent()
    agent.run(args.folders)


if __name__ == "__main__":
    main()
