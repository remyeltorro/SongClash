"""The battle screen: two stacked song cards, tap a title to vote."""

from __future__ import annotations

import asyncio

import toga
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN, HIDDEN, VISIBLE

from songclash.core.models import song_caption
from songclash.core.session import ALL_ALBUMS
from songclash.mobile import theme
from songclash.mobile.audio import IDLE, LOADING, MISSING, PLAYING

SIDES = ("A", "B")
CORNER_NAMES = {"A": "TEAL CORNER", "B": "ORANGE CORNER"}
AUDIO_TEXT = {
    IDLE: "▶  Preview",
    LOADING: "⏳  Loading…",
    PLAYING: "■  Stop",
    MISSING: "✖  No preview",
}
COVER_SIZE = 116


class SongCard:
    """One corner: cover, title (the vote button), caption, preview button."""

    def __init__(self, side, on_vote, on_preview):
        color, dim = theme.SIDE_COLORS[side]
        self.cover = toga.ImageView(style=Pack(width=COVER_SIZE, height=COVER_SIZE, background_color=dim))
        self.title = toga.Button(
            "-",
            on_press=lambda w, **kw: on_vote(side),
            style=theme.button(color=dim, text_color=theme.TEXT, height=76, font_size=17),
        )
        self.caption = toga.Label("", style=theme.text(12, theme.MUTED))
        self.audio = toga.Button(
            AUDIO_TEXT[IDLE],
            on_press=lambda w, **kw: on_preview(side),
            style=theme.button(color=theme.SURFACE_HI, text_color=color, height=44),
        )
        self.progress = toga.ProgressBar(max=100, value=0, style=Pack(visibility=HIDDEN))

        details = toga.Box(
            children=[self.title, self.caption, self.audio],
            style=Pack(direction=COLUMN, flex=1, gap=6),
        )
        self.box = toga.Box(
            children=[
                toga.Label(CORNER_NAMES[side], style=theme.heading(12, color)),
                toga.Box(children=[self.cover, details], style=theme.row(gap=10)),
                self.progress,
            ],
            style=Pack(direction=COLUMN, background_color=theme.SURFACE, margin=10, gap=6),
        )

    def show(self, song, covers):
        self.title.text = song["title"]
        self.caption.text = song_caption(song)
        covers.show(self.cover, song.get("cover_url"))

    def clear(self):
        self.title.text = "-"
        self.caption.text = ""
        self.cover.image = None

    def set_enabled(self, enabled):
        self.title.enabled = enabled
        self.audio.enabled = enabled

    def set_audio_state(self, state):
        self.audio.text = AUDIO_TEXT[state]
        self.progress.style.visibility = VISIBLE if state == PLAYING else HIDDEN
        if state != PLAYING:
            self.progress.value = 0


class BattleScreen:
    def __init__(self, controller):
        self.c = controller
        self.cards = {side: SongCard(side, controller.vote, controller.toggle_preview) for side in SIDES}
        self._progress_task = None

        self.album = toga.Selection(items=[ALL_ALBUMS], on_change=self._on_album_changed, style=Pack(flex=1))
        self.btn_undo = toga.Button(
            "↶ Undo", on_press=lambda w, **kw: controller.undo(), style=theme.button(flex=1)
        )
        self.btn_skip = toga.Button(
            "Skip ↷", on_press=lambda w, **kw: controller.skip(), style=theme.button(flex=1)
        )
        vs = toga.Label("VS", style=theme.heading(22, text_align=CENTER, width=56))
        self.stats = toga.Label("", style=theme.text(12, theme.GOLD, text_align=CENTER))

        self.arena = toga.Box(
            children=[
                toga.Box(
                    children=[toga.Label("Album", style=theme.text(13, theme.MUTED)), self.album],
                    style=theme.row(gap=8),
                ),
                self.cards["A"].box,
                toga.Box(children=[self.btn_undo, vs, self.btn_skip], style=theme.row(gap=8)),
                self.cards["B"].box,
                self.stats,
            ],
            style=Pack(direction=COLUMN, gap=10),
        )
        self.welcome = toga.Box(
            children=[
                toga.Label("SongClash", style=theme.heading(30, text_align=CENTER)),
                toga.Label(
                    "Rank an artist's songs through head-to-head battles.\nAdd an artist to get started.",
                    style=theme.text(15, theme.MUTED, text_align=CENTER),
                ),
                toga.Button(
                    "＋  Add an Artist",
                    on_press=lambda w, **kw: controller.show("import"),
                    style=theme.button(color=theme.GOLD, text_color=theme.BG, height=56),
                ),
                toga.Button(
                    "Open a Saved Session",
                    on_press=lambda w, **kw: controller.show("sessions"),
                    style=theme.button(),
                ),
            ],
            style=Pack(direction=COLUMN, gap=16, margin_top=40),
        )
        self.page = toga.Box(style=theme.page())
        self.box = toga.ScrollContainer(
            content=self.page, horizontal=False, style=Pack(flex=1, background_color=theme.BG)
        )
        self._album_items = [ALL_ALBUMS]
        self._updating = False

    # ---------- Display ----------

    def refresh(self):
        s = self.c.session
        page = self.arena if s.songs else self.welcome
        if self.page.children != [page]:
            self.page.clear()
            self.page.add(page)
        items = [ALL_ALBUMS, *s.get_albums_list()]
        if s.active_filter not in items:
            s.active_filter = ALL_ALBUMS
        self._updating = True
        try:
            if items != self._album_items:
                self._album_items = items
                self.album.items = items
            self.album.value = s.active_filter
        finally:
            self._updating = False
        self.refresh_stats()

    def refresh_stats(self):
        s = self.c.session
        self.stats.text = f"{len(s.songs)} songs  ·  {s.votes_this_session} votes this session"
        self.btn_undo.enabled = bool(s.undo_stack)

    def show_pair(self, songs):
        """Display two songs, or disabled cards if ``songs`` is None."""
        for i, side in enumerate(SIDES):
            card = self.cards[side]
            card.set_enabled(songs is not None)
            if songs is None:
                card.clear()
            else:
                card.show(songs[i], self.c.covers)
        self.btn_skip.enabled = songs is not None

    def set_audio_state(self, side, state):
        self.cards[side].set_audio_state(state)
        if state == PLAYING and self._progress_task is None:
            self._progress_task = asyncio.ensure_future(self._track_progress(side))

    async def _track_progress(self, side):
        try:
            while self.c.audio.active_side == side:
                self.cards[side].progress.value = 100 * self.c.audio.progress()
                await asyncio.sleep(0.25)
        finally:
            self._progress_task = None

    def _on_album_changed(self, widget, **kw):
        if not self._updating and widget.value is not None:
            self.c.set_filter(widget.value)
