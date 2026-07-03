"""
commit_generator.py
Generates human-readable, conventional-commit-style messages by analyzing
the actual staged/unstaged file changes reported by GitManager, rather
than using a generic "update files" message.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List

EXTENSION_LABELS = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "React",
    ".ts": "TypeScript",
    ".tsx": "React",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "config",
    ".yaml": "config",
    ".yml": "config",
    ".md": "docs",
}


class CommitGenerator:
    """Builds intelligent commit messages from a file-change summary."""

    MAX_LISTED_FILES = 5

    def generate(self, status: Dict[str, List[str]]) -> str:
        added = status.get("added", []) + status.get("untracked", [])
        modified = status.get("modified", [])
        deleted = status.get("deleted", [])

        added = sorted(set(added))
        modified = sorted(set(modified))
        deleted = sorted(set(deleted))

        if not added and not modified and not deleted:
            return "chore: sync minor changes"

        prefix = self._determine_prefix(added, modified, deleted)
        summary = self._build_summary(added, modified, deleted)
        detail = self._build_detail_line(added, modified, deleted)

        message = f"{prefix}: {summary}"
        if detail:
            message += f"\n\n{detail}"
        return message

    # ------------------------------------------------------------------
    @staticmethod
    def _determine_prefix(added: List[str], modified: List[str], deleted: List[str]) -> str:
        if deleted and not added and not modified:
            return "chore"
        if added and not modified and not deleted:
            return "feat"
        if modified and not added and not deleted:
            return "fix"
        return "chore"

    @classmethod
    def _build_summary(cls, added: List[str], modified: List[str], deleted: List[str]) -> str:
        parts = []
        if added:
            parts.append(f"add {len(added)} file(s)")
        if modified:
            parts.append(f"update {len(modified)} file(s)")
        if deleted:
            parts.append(f"remove {len(deleted)} file(s)")

        lang_counter = Counter()
        for f in added + modified:
            ext = Path(f).suffix.lower()
            if ext in EXTENSION_LABELS:
                lang_counter[EXTENSION_LABELS[ext]] += 1

        summary = ", ".join(parts)
        if lang_counter:
            top_lang = lang_counter.most_common(1)[0][0]
            summary += f" ({top_lang})"
        return summary

    @classmethod
    def _build_detail_line(cls, added: List[str], modified: List[str], deleted: List[str]) -> str:
        lines = []
        for label, files in (("Added", added), ("Modified", modified), ("Deleted", deleted)):
            if not files:
                continue
            shown = files[: cls.MAX_LISTED_FILES]
            extra = len(files) - len(shown)
            file_list = ", ".join(shown)
            if extra > 0:
                file_list += f", +{extra} more"
            lines.append(f"{label}: {file_list}")
        return "\n".join(lines)
