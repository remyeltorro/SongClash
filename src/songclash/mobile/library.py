"""Where the mobile app keeps its sessions and settings.

Phones have no "Save As" workflow, so every session lives as a JSON file in
the app's private data folder and is saved after every change. The files use
the desktop format, so they can be exported and opened in the desktop app.

Plain Python (no Toga), so it is unit tested directly.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from songclash.core import storage


@dataclass
class SessionInfo:
    path: Path
    name: str
    songs: int
    modified: float


def safe_name(name: str) -> str:
    """A file name stem from free text ("AC/DC" -> "AC-DC")."""
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "-", name).strip(" .-")
    return stem[:60] or "Session"


class SessionLibrary:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)
        self.sessions_dir = self.root / "sessions"
        self.settings_path = self.root / "settings.json"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Sessions ----------

    def sessions(self) -> list[SessionInfo]:
        """Saved sessions, most recently changed first. Unreadable files are skipped."""
        found = []
        for path in self.sessions_dir.glob("*.json"):
            try:
                count = len(storage.read_session(path))
            except (OSError, ValueError):
                continue
            found.append(SessionInfo(path, path.stem, count, path.stat().st_mtime))
        found.sort(key=lambda s: s.modified, reverse=True)
        return found

    def new_path(self, name: str) -> Path:
        """A path for a new session called ``name`` that doesn't clash."""
        stem = safe_name(name)
        path = self.sessions_dir / f"{stem}.json"
        n = 2
        while path.exists():
            path = self.sessions_dir / f"{stem} ({n}).json"
            n += 1
        return path

    def rename(self, path: str | os.PathLike, name: str) -> Path:
        path = Path(path)
        if safe_name(name) == path.stem:
            return path
        target = self.new_path(name)
        path.rename(target)
        return target

    def delete(self, path: str | os.PathLike) -> None:
        Path(path).unlink(missing_ok=True)

    # ---------- Settings ----------

    def settings(self) -> dict:
        try:
            with open(self.settings_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def update_settings(self, **values) -> None:
        data = self.settings()
        data.update(values)
        tmp = self.settings_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.settings_path)

    def last_session(self) -> Path | None:
        name = self.settings().get("last_session")
        path = self.sessions_dir / name if name else None
        return path if path and path.is_file() else None

    def set_last_session(self, path: str | os.PathLike | None) -> None:
        self.update_settings(last_session=Path(path).name if path else None)
