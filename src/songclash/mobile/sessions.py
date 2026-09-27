"""Saved sessions: switch, rename, delete, import and export."""

from __future__ import annotations

import functools
import time

import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from songclash.mobile import theme


class SessionsScreen:
    def __init__(self, controller):
        self.c = controller
        self.name = toga.TextInput(on_confirm=self.rename, style=Pack(flex=1))
        self.current = toga.Label("", style=theme.text(12, theme.MUTED))
        self.rows = toga.Box(style=Pack(direction=COLUMN, gap=8))
        content = toga.Box(
            children=[
                toga.Label("Current Session", style=theme.heading(18)),
                toga.Box(
                    children=[
                        self.name,
                        theme.Button("Rename", on_press=self.rename, style=theme.button(width=100)),
                    ],
                    style=theme.row(gap=8),
                ),
                self.current,
                toga.Box(
                    children=[
                        theme.Button("New Session", on_press=self.new_session, style=theme.button(flex=1)),
                        theme.Button("Export File", on_press=self.export, style=theme.button(flex=1)),
                    ],
                    style=theme.row(gap=8),
                ),
                theme.Button(
                    "Import Session File…",
                    on_press=self.import_file,
                    style=theme.button(),
                ),
                toga.Label(
                    theme.wrap("Session files are compatible with the SongClash desktop app.", size=12),
                    style=theme.text(12, theme.MUTED),
                ),
                toga.Label("Saved Sessions", style=theme.heading(18, margin_top=10)),
                self.rows,
            ],
            style=theme.page(),
        )
        self.box = toga.ScrollContainer(
            content=content, horizontal=False, style=Pack(flex=1, background_color=theme.BG)
        )

    def refresh(self):
        s = self.c.session
        self.name.value = self.c.session_name()
        self.current.text = f"{len(s.songs)} songs · saved automatically"
        self.rows.clear()
        sessions = self.c.library.sessions()
        if not sessions:
            self.rows.add(toga.Label("No saved sessions yet.", style=theme.text(13, theme.MUTED)))
        for info in sessions:
            is_current = s.current_filename is not None and info.path.samefile(s.current_filename)
            when = time.strftime("%d %b %Y, %H:%M", time.localtime(info.modified))
            name = theme.wrap(f"{'● ' if is_current else ''}{info.name}", 270, 14)
            label = f"{name}\n{info.songs} songs · {when}"
            self.rows.add(
                toga.Box(
                    children=[
                        theme.Button(
                            label,
                            on_press=functools.partial(self._open, info.path),
                            style=theme.button(
                                color=theme.SURFACE,
                                text_color=theme.GOLD if is_current else theme.TEXT,
                                height=64,
                                font_size=14,
                                flex=1,
                            ),
                        ),
                        theme.Button(
                            "✕",
                            on_press=functools.partial(self._delete, info),
                            style=theme.button(
                                color=theme.SURFACE, text_color=theme.RED, width=52, height=64
                            ),
                        ),
                    ],
                    style=theme.row(gap=6),
                )
            )

    def _open(self, path, widget, **kw):
        self.c.open_session(path)

    async def _delete(self, info, widget, **kw):
        if await self.c.confirm(
            "Delete Session", f"Delete '{info.name}' ({info.songs} songs)? This can't be undone."
        ):
            self.c.delete_session(info.path)

    def rename(self, widget, **kw):
        self.c.rename_session(self.name.value)

    def new_session(self, widget, **kw):
        self.c.new_session()

    async def export(self, widget, **kw):
        await self.c.export_session()

    async def import_file(self, widget, **kw):
        await self.c.import_session_file()
