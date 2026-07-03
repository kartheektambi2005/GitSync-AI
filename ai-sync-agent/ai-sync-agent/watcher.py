"""
watcher.py
File-system monitoring built on top of `watchdog`. Detects file/folder
creation, modification, deletion and renames. Applies debounce logic so
rapid successive saves collapse into a single sync trigger. Also provides
lightweight project-type detection heuristics.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from logger_manager import get_logger
from settings import settings

log = get_logger("watcher")

SyncCallback = Callable[[str], None]  # called with folder_path after debounce fires


# ---------------------------------------------------------------------------
# Project type detection
# ---------------------------------------------------------------------------
def detect_project_type(folder_path: str) -> str:
    """Best-effort detection of the project type based on marker files."""
    root = Path(folder_path)

    markers = [
        (root / "package.json", None),
        (root / "requirements.txt", "Python"),
        (root / "pyproject.toml", "Python"),
        (root / "pom.xml", "Java"),
        (root / "build.gradle", "Java"),
        (root / "index.html", "HTML/CSS"),
    ]

    package_json = root / "package.json"
    if package_json.exists():
        try:
            content = package_json.read_text(encoding="utf-8", errors="ignore")
            if '"react"' in content:
                return "React"
            return "Node.js/JavaScript"
        except OSError:
            return "Node.js/JavaScript"

    for path, label in markers:
        if label and path.exists():
            return label

    # Fallback: scan file extensions shallowly
    ext_counts: Dict[str, int] = {}
    try:
        for p in root.rglob("*"):
            if p.is_file() and not _is_ignored(p):
                ext_counts[p.suffix.lower()] = ext_counts.get(p.suffix.lower(), 0) + 1
            if sum(ext_counts.values()) > 500:
                break
    except OSError:
        pass

    if ext_counts.get(".py", 0) > 0:
        return "Python"
    if ext_counts.get(".java", 0) > 0:
        return "Java"
    if ext_counts.get(".jsx", 0) or ext_counts.get(".tsx", 0):
        return "React"
    if ext_counts.get(".js", 0) > 0:
        return "JavaScript"
    if ext_counts.get(".html", 0) > 0 or ext_counts.get(".css", 0) > 0:
        return "HTML/CSS"

    return "unknown"


def _is_ignored(path: Path) -> bool:
    if any(part in settings.IGNORED_DIR_NAMES for part in path.parts):
        return True
    if path.suffix in settings.IGNORED_FILE_SUFFIXES:
        return True
    return False


# ---------------------------------------------------------------------------
# Debounce handler
# ---------------------------------------------------------------------------
class DebouncedEventHandler(FileSystemEventHandler):
    """
    Collects filesystem events for a folder and fires `on_settled` only
    after `debounce_seconds` have elapsed with no further events -
    preventing a flood of commits for rapid successive saves.
    """

    def __init__(self, folder_path: str, debounce_seconds: float, on_settled: SyncCallback):
        super().__init__()
        self.folder_path = folder_path
        self.debounce_seconds = debounce_seconds
        self.on_settled = on_settled
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _record_event(self, event: FileSystemEvent) -> None:
        if _is_ignored(Path(event.src_path)):
            return
        log.info(f"[{Path(self.folder_path).name}] {event.event_type}: {event.src_path}")
        self._reset_timer()

    def _reset_timer(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        try:
            self.on_settled(self.folder_path)
        except Exception as exc:  # noqa: BLE001
            log.error(f"Error handling settled changes for {self.folder_path}: {exc}")

    # watchdog event hooks -------------------------------------------------
    def on_created(self, event: FileSystemEvent) -> None:
        self._record_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._record_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._record_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._record_event(event)


# ---------------------------------------------------------------------------
# Multi-folder watcher manager
# ---------------------------------------------------------------------------
class FolderWatcher:
    """Manages watchdog Observers for one or more folders simultaneously."""

    def __init__(self, on_settled: SyncCallback):
        self.on_settled = on_settled
        self._observer = Observer()
        self._handlers: Dict[str, DebouncedEventHandler] = {}
        self._started = False

    def watch(self, folder_path: str, debounce_seconds: Optional[float] = None) -> None:
        folder_path = str(Path(folder_path).expanduser().resolve())
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        handler = DebouncedEventHandler(
            folder_path,
            debounce_seconds or settings.DEBOUNCE_SECONDS,
            self.on_settled,
        )
        self._handlers[folder_path] = handler
        self._observer.schedule(handler, folder_path, recursive=True)
        log.info(f"Watching folder: {folder_path}")

    def start(self) -> None:
        if not self._started:
            self._observer.start()
            self._started = True
            log.info("File system observer started.")

    def stop(self) -> None:
        if self._started:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._started = False
            log.info("File system observer stopped.")
