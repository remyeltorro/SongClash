"""Persistent user preferences (QSettings: the registry on Windows)."""

import os

from PyQt6.QtCore import QSettings

from songclash import APP_NAME

MAX_RECENT = 8


class AppSettings:
    """Typed access to the values SongClash remembers between runs."""

    def __init__(self, qsettings: QSettings | None = None):
        self.qs = qsettings or QSettings(APP_NAME, APP_NAME)

    def _list(self, name):
        # QSettings returns a bare string for one-item lists on some backends
        value = self.qs.value(name, [])
        return [value] if isinstance(value, str) else list(value or [])

    # Recent session files
    def recent_files(self) -> list[str]:
        return self._list("recent_files")

    def add_recent(self, fname):
        fname = os.path.abspath(fname)
        files = [f for f in self.recent_files() if f != fname]
        self.qs.setValue("recent_files", [fname] + files[: MAX_RECENT - 1])

    def remove_recent(self, fname):
        fname = os.path.abspath(fname)
        self.qs.setValue("recent_files", [f for f in self.recent_files() if f != fname])

    def last_dir(self) -> str:
        files = self.recent_files()
        return os.path.dirname(files[0]) if files else ""

    # Import dialog choices
    def import_types(self) -> list[str]:
        return self._list("import_types")

    def set_import_types(self, types):
        self.qs.setValue("import_types", list(types))
