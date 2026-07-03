import time
from pathlib import Path

from watcher import DebouncedEventHandler, detect_project_type


def test_detect_python_project(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    assert detect_project_type(str(tmp_path)) == "Python"


def test_detect_node_project(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "app", "dependencies": {}}')
    assert detect_project_type(str(tmp_path)) == "Node.js/JavaScript"


def test_detect_react_project(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "app", "dependencies": {"react": "^18.0.0"}}')
    assert detect_project_type(str(tmp_path)) == "React"


def test_detect_html_project(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>")
    assert detect_project_type(str(tmp_path)) == "HTML/CSS"


def test_detect_unknown_project(tmp_path: Path):
    assert detect_project_type(str(tmp_path)) == "unknown"


def test_debounce_collapses_rapid_events(tmp_path: Path):
    calls = []

    def on_settled(folder_path: str) -> None:
        calls.append(folder_path)

    handler = DebouncedEventHandler(str(tmp_path), debounce_seconds=0.2, on_settled=on_settled)

    class FakeEvent:
        def __init__(self, path: str, event_type: str = "modified"):
            self.src_path = path
            self.event_type = event_type

    for _ in range(5):
        handler.on_modified(FakeEvent(str(tmp_path / "file.txt")))
        time.sleep(0.05)

    time.sleep(0.4)
    assert len(calls) == 1
