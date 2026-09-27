"""Saved sessions: switch, rename, delete, import and export."""

from __future__ import annotations

import functools
import time

import toga
from toga.style import Pack
from toga.style.pack import BOLD, COLUMN

from songclash.mobile import device, theme
from songclash.mobile.rankings import header


class SessionsScreen:
    def __init__(self, controller):
        self.c = controller
        self.name = theme.text_input(on_confirm=self.rename)
        self.current = theme.muted("", 13)
        self.rows = toga.Box(style=Pack(direction=COLUMN, gap=8))
        content = toga.Box(
            children=[
                header("☰  Sessions", "Saved automatically after every vote"),
                theme.card(
                    theme.corner_tag("CURRENT SESSION", theme.GOLD, 11),
                    toga.Box(
                        children=[self.name, theme.pill("Rename", self.rename, "surface", 40, width=96)],
                        style=theme.row(gap=10),
                    ),
                    self.current,
                    toga.Box(
                        children=[
                            theme.pill("＋  New", self.new_session, "surface", 44, flex=1),
                            theme.pill("⤓  Export", self.export, "surface", 44, flex=1),
                        ],
                        style=theme.row(gap=10, margin=(4, 0, 0, 0)),
                    ),
                    padding=16,
                    gap=10,
                    stroke=theme.GOLD,
                ),
                theme.pill("⤒  Import a Session File…", self.import_file, "ghost", 46),
                theme.muted(theme.wrap("Session files work in the SongClash desktop app too.", size=12), 12),
                theme.corner_tag("SAVED SESSIONS", theme.MUTED, 11),
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
        self.current.text = f"{len(s.songs)} songs · {s.votes_this_session} votes this session"
        self.rows.clear()
        sessions = self.c.library.sessions()
        if not sessions:
            self.rows.add(theme.muted("No saved sessions yet."))
        for info in sessions:
            is_current = s.current_filename is not None and info.path.samefile(s.current_filename)
            self.rows.add(self._row(info, is_current))

    def _row(self, info, is_current):
        when = time.strftime("%d %b %Y, %H:%M", time.localtime(info.modified))
        details = toga.Box(
            children=[
                toga.Label(
                    theme.wrap(info.name, 250, 16),
                    style=theme.text(16, theme.GOLD if is_current else theme.TEXT, font_weight=BOLD),
                ),
                theme.muted(f"{info.songs} songs · {when}" + ("  ·  open" if is_current else ""), 12),
            ],
            style=Pack(direction=COLUMN, flex=1, gap=2),
        )
        delete = theme.pill("✕", functools.partial(self._delete, info), "danger", 40, width=44, size=16)
        row = toga.Box(children=[details, delete], style=theme.row(gap=10, margin=(10, 10, 10, 16)))
        card = theme.skin(
            toga.Box(children=[row], style=Pack(direction=COLUMN)),
            fill=theme.SURFACE,
            stroke=theme.GOLD if is_current else theme.BORDER,
            radius=14,
            ripple=theme.RIPPLE,
        )
        if not device.on_tap(card, lambda: self.c.open_session(info.path)):
            row.insert(1, theme.pill("Open", lambda w, **kw: self.c.open_session(info.path), "ghost", 40))
        return card

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
