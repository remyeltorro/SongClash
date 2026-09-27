"""The battle screen: two stacked corners, tap a song's title card to vote."""

from __future__ import annotations

import asyncio

import toga
from toga.style import Pack
from toga.style.pack import BOLD, CENTER, COLUMN

from songclash.core.models import song_caption
from songclash.core.session import ALL_ALBUMS
from songclash.mobile import device, theme
from songclash.mobile.audio import IDLE, LOADING, MISSING, PLAYING
from songclash.resources import APP_ICON

SIDES = ("A", "B")
CORNER_NAMES = {"A": "TEAL CORNER", "B": "ORANGE CORNER"}
SIDE_KINDS = {"A": "teal", "B": "orange"}
AUDIO = {  # state -> (text, pill kind; None means the side's gradient)
    IDLE: ("▶  Play", None),
    LOADING: ("⏳  Loading", "ghost"),
    PLAYING: ("■  Stop", "outline"),
    MISSING: ("✖  No preview", "ghost"),
}
COVER = 112
TITLE_WIDTH = 215  # dp available for the title text inside its card


class SongCard:
    """One corner: cover, title card (the vote target), caption, preview."""

    def __init__(self, side, on_vote, on_preview):
        self.side = side
        color, dim = theme.SIDE_COLORS[side]

        # The cover sits in a frame bordered with the corner's color
        self.cover = toga.ImageView(style=Pack(width=COVER - 8, height=COVER - 8, margin=4))
        theme.skin(self.cover, fill=dim, radius=9)
        frame = theme.skin(toga.Box(children=[self.cover]), fill=dim, stroke=color, stroke_width=2, radius=12)

        self.title = theme.Button(
            "-",
            on_press=lambda w, **kw: on_vote(side),
            style=Pack(flex=1, height=COVER + 8, font_size=19, font_weight=BOLD, color=theme.TEXT),
        )
        theme.skin(
            self.title,
            gradient=[theme.SURFACE_HI, theme.SURFACE],
            vertical=True,
            stroke=theme.BORDER,
            stroke_width=2,
            radius=16,
            ripple="#55" + color[1:],  # the corner's color, translucent
        )

        self.caption = theme.muted("", 13, flex=1)
        self.audio = theme.pill(
            AUDIO[IDLE][0], lambda w, **kw: on_preview(side), SIDE_KINDS[side], 38, size=14, width=124
        )
        self.progress = toga.ProgressBar(max=100, value=0)
        # Holds the progress bar only while playing, so it takes no room otherwise
        self.progress_slot = toga.Box(style=Pack(direction=COLUMN))
        device.tint(self.progress, color)

        self.box = theme.card(
            theme.corner_tag(CORNER_NAMES[side], color),
            toga.Box(children=[frame, self.title], style=theme.row(gap=10)),
            toga.Box(children=[self.caption, self.audio], style=theme.row(gap=10)),
            self.progress_slot,
            gap=10,
        )

    def show(self, song, covers):
        self.title.text = theme.wrap(song["title"], TITLE_WIDTH, 19)
        self.caption.text = theme.wrap(song_caption(song), 220, 13)
        covers.show(self.cover, song.get("cover_url"))

    def clear(self):
        self.title.text = "—"
        self.caption.text = ""
        self.cover.image = None

    def set_enabled(self, enabled):
        self.title.enabled = enabled
        self.audio.enabled = enabled

    def set_audio_state(self, state):
        label, kind = AUDIO[state]
        self.audio.text = label
        if kind is None:
            kind = SIDE_KINDS[self.side]
        elif kind == "outline":
            kind = SIDE_KINDS[self.side] + "_outline"
        theme.restyle(self.audio, kind)
        if state == PLAYING and not self.progress_slot.children:
            self.progress_slot.add(self.progress)
        elif state != PLAYING and self.progress_slot.children:
            self.progress_slot.clear()
        if state != PLAYING:
            self.progress.value = 0


class BattleScreen:
    def __init__(self, controller):
        self.c = controller
        self.cards = {side: SongCard(side, controller.vote, controller.toggle_preview) for side in SIDES}
        self._progress_task = None

        self.album = toga.Selection(
            items=[ALL_ALBUMS], on_change=self._on_album_changed, style=Pack(flex=1, color=theme.TEXT)
        )
        device.tint(self.album, theme.MUTED)
        weight_class = theme.card(
            theme.corner_tag("WEIGHT CLASS", theme.MUTED, 10),
            toga.Box(
                children=[self.album, toga.Label("▾", style=theme.text(18, theme.MUTED))],
                style=theme.row(gap=6),
            ),
            padding=(8, 12),
            gap=0,
            radius=12,
            stroke_width=1,
        )

        self.btn_undo = theme.pill("↶  Undo", lambda w, **kw: controller.undo(), "ghost", 40, flex=1)
        self.btn_skip = theme.pill("Skip  ↷", lambda w, **kw: controller.skip(), "ghost", 40, flex=1)
        self.stats = toga.Label("", style=theme.text(13, theme.GOLD, text_align=CENTER, font_weight=BOLD))

        self.arena = toga.Box(
            children=[
                weight_class,
                self.cards["A"].box,
                toga.Box(
                    children=[self.btn_undo, theme.vs_emblem(), self.btn_skip],
                    style=theme.row(gap=12, margin=(0, 4)),
                ),
                self.cards["B"].box,
                self.stats,
            ],
            style=Pack(direction=COLUMN, gap=12),
        )
        self.welcome = self._build_welcome()
        self.page = toga.Box(style=theme.page())
        self.box = toga.ScrollContainer(
            content=self.page, horizontal=False, style=Pack(flex=1, background_color=theme.BG)
        )
        self._album_items = [ALL_ALBUMS]
        self._updating = False

    def _build_welcome(self):
        tagline = theme.corner_tag("HEAD-TO-HEAD SONG RANKING", theme.GOLD, 12)
        tagline.style.text_align = CENTER
        return toga.Box(
            children=[
                toga.ImageView(toga.Image(APP_ICON), style=Pack(width=150, height=150, margin=(24, 0, 8, 0))),
                tagline,
                toga.Label(
                    "SongClash",
                    style=theme.heading(44, theme.TEXT, text_align=CENTER, margin=(0, 0, 4, 0)),
                ),
                theme.muted(
                    theme.wrap(
                        "Settle an artist's discography one battle at a time. "
                        "Your picks become a ranking, the Elo way.",
                        size=16,
                    ),
                    16,
                    text_align=CENTER,
                ),
                toga.Box(style=Pack(height=16)),
                theme.pill("＋  Add an Artist", lambda w, **kw: self.c.show("import"), "gold", 52, size=17),
                theme.pill("Open a Saved Session", lambda w, **kw: self.c.show("sessions"), "ghost", 48),
            ],
            style=Pack(direction=COLUMN, align_items=CENTER, gap=12),
        )

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
        self.stats.text = f"{len(s.songs)} songs  |  {s.votes_this_session} votes this session"
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
