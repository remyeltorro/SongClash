"""Song and album leaderboards, their detail sheets, and the song forms."""

from __future__ import annotations

import toga
from toga.style import Pack
from toga.style.pack import BOLD, COLUMN, RIGHT

from songclash.core.export import ranking_csv
from songclash.core.models import song_caption
from songclash.core.session import ALL_ALBUMS
from songclash.mobile import device, theme
from songclash.mobile.library import safe_name


def rank_label(rank: int) -> str:
    return f"{theme.MEDAL_ICONS[rank - 1]} {rank}" if rank <= len(theme.MEDALS) else str(rank)


def rank_color(rank: int, default=theme.TEXT) -> str:
    return theme.MEDALS[rank - 1] if rank <= len(theme.MEDALS) else default


def tappable_row(children, on_tap, rank):
    """A leaderboard row: alternating stripes like the desktop table, tap to open."""
    row = toga.Box(children=children, style=theme.row(gap=12, margin=(10, 12)))
    outer = toga.Box(children=[row], style=Pack(direction=COLUMN))
    theme.skin(
        outer,
        fill=theme.SURFACE if rank % 2 else theme.SURFACE_HI,
        stroke=theme.MEDALS[rank - 1] if rank <= len(theme.MEDALS) else None,
        stroke_width=1,
        radius=12,
        ripple=theme.RIPPLE,
    )
    if not device.on_tap(outer, on_tap):
        # No native tap handling (desktop preview): add a button instead
        row.add(theme.pill("›", lambda w, **kw: on_tap(), "ghost", 36, width=40))
    return outer


def header(title, subtitle=None):
    children = [toga.Label(title, style=theme.heading(22))]
    if subtitle:
        children.append(theme.muted(theme.wrap(subtitle, size=13)))
    return toga.Box(children=children, style=Pack(direction=COLUMN, gap=2))


def scroller(content):
    return toga.ScrollContainer(
        content=content, horizontal=False, style=Pack(flex=1, background_color=theme.BG)
    )


# Without a native list (desktop preview), rows are Toga widgets built in
# pages: a whole discography at once takes far too long.
PAGE_SIZE = 50


def column_of(children, gap=6):
    """A column built with its children up front: one layout pass, not one per child."""
    return toga.Box(children=children, style=Pack(direction=COLUMN, gap=gap))


class SongsScreen:
    """Ranked songs for the current album filter. Tap a song to edit it.

    On Android the rows live in a recycling native list (``device.NativeList``),
    which stays instant for thousands of songs.
    """

    def __init__(self, controller):
        self.c = controller
        self.keys: list[str] = []
        self.shown = 0
        self.header = toga.Box(style=Pack(direction=COLUMN))
        self.rows = column_of([])
        self.more = theme.pill("", self.show_more, "ghost", 44)
        if device.IS_ANDROID:
            self.list = toga.Box(style=Pack(flex=1))
            self.native = device.NativeList(
                self.list,
                self.open_song,
                {"text": theme.TEXT, "muted": theme.MUTED, "ripple": theme.RIPPLE},
            )
        else:
            self.list = scroller(self.rows)
            self.native = None
        actions = toga.Box(
            children=[
                theme.pill("＋  Add Song", self.add_song, "teal", 42, flex=1),
                theme.pill("⤓  Export CSV", self.export_csv, "gold", 42, flex=1),
            ],
            style=theme.row(gap=10),
        )
        self.box = toga.Box(children=[self.header, actions, self.list], style=theme.page())

    def refresh(self):
        s = self.c.session
        self.header.clear()
        self.header.add(header("♛  Leaderboard", f"{s.active_filter} · tap a song to merge or delete it"))
        self.keys = s.ranked_keys()
        if self.native:
            self.native.set_rows([self._row_data(rank, s.songs[k]) for rank, k in enumerate(self.keys, 1)])
            return
        self.shown = 0
        # Fill a detached box, then swap it in: laid out once, off screen
        self.rows = column_of([])
        self.show_more()
        self.list.content = self.rows

    def show_more(self, widget=None, **kw):
        songs = self.c.session.songs
        end = min(self.shown + PAGE_SIZE, len(self.keys))
        batch = [
            self._row(rank, key, songs[key])
            for rank, key in enumerate(self.keys[self.shown : end], self.shown + 1)
        ]
        if self.more in self.rows.children:
            self.rows.remove(self.more)
        self.rows.add(column_of(batch))
        self.shown = end
        if left := len(self.keys) - end:
            self.more.text = f"Show {min(PAGE_SIZE, left)} more  ·  {left} left"
            self.rows.add(self.more)

    def _row_data(self, rank, song):
        top = rank <= len(theme.MEDALS)
        return {
            "rank": rank_label(rank),
            "rank_color": rank_color(rank, theme.MUTED),
            "title": song["title"],
            "title_color": rank_color(rank),
            "bold": top,
            "subtitle": song["album"],
            "score": str(round(song["score"])),
            "votes": f"{song['matches']} votes",
            "fill": theme.SURFACE if rank % 2 else theme.SURFACE_HI,
            "stroke": theme.MEDALS[rank - 1] if top else None,
        }

    def open_song(self, position):
        if position < len(self.keys):
            self.c.show_screen(SongSheet(self.c, self.keys[position], position + 1))

    def _row(self, rank, key, song):
        color = rank_color(rank)
        top = rank <= len(theme.MEDALS)
        info = toga.Box(
            children=[
                toga.Label(
                    theme.wrap(song["title"], 200, 16),
                    style=theme.text(16, color, font_weight=BOLD if top else "normal"),
                ),
                theme.muted(theme.wrap(song["album"], 200, 12), 12),
            ],
            style=Pack(direction=COLUMN, flex=1, gap=2),
        )
        score = toga.Box(
            children=[
                toga.Label(
                    str(round(song["score"])),
                    style=theme.text(16, theme.TEXT, font_weight=BOLD, text_align=RIGHT),
                ),
                theme.muted(f"{song['matches']} votes", 11, text_align=RIGHT),
            ],
            style=Pack(direction=COLUMN, width=64),
        )
        rank_text = toga.Label(
            rank_label(rank), style=theme.text(15, rank_color(rank, theme.MUTED), font_weight=BOLD, width=48)
        )
        return tappable_row(
            [rank_text, info, score], lambda: self.c.show_screen(SongSheet(self.c, key, rank)), rank
        )

    def add_song(self, widget, **kw):
        self.c.show_screen(AddSongForm(self.c))

    async def export_csv(self, widget, **kw):
        s = self.c.session
        keys = s.ranked_keys()
        if not keys:
            await self.c.info("Export", "No songs to export!")
            return
        name = s.active_filter if s.active_filter != ALL_ALBUMS else self.c.session_name()
        content = ranking_csv(s.songs[k] for k in keys).encode("utf-8-sig")
        saved = await self.c.save_document(
            "Export Ranking", f"{safe_name(name)} ranking.csv", "text/csv", content
        )
        if saved:
            await self.c.info(
                "Export Successful",
                f"Exported {len(keys)} songs to {saved}.\n\n"
                "You can import this CSV into Spotify with Soundiiz or TuneMyMusic.",
            )


def stat(value, label, color=theme.TEXT):
    return toga.Box(
        children=[
            toga.Label(value, style=theme.heading(22, color)),
            theme.corner_tag(label, theme.MUTED, 10),
        ],
        style=Pack(direction=COLUMN, flex=1, gap=2),
    )


def back_button(controller, screen):
    return theme.pill("‹  Back", lambda w, **kw: controller.show(screen), "ghost", 44)


class SongSheet:
    """One song: its stats, and the edits you can make to it."""

    def __init__(self, controller, key, rank):
        self.c = controller
        self.key = key
        song = controller.session.songs[key]
        color = rank_color(rank)
        self.box = toga.Box(
            children=[
                theme.card(
                    theme.corner_tag(f"RANK #{rank}", color),
                    toga.Label(theme.wrap(song["title"], 330, 24), style=theme.heading(24, theme.TEXT)),
                    theme.muted(theme.wrap(song_caption(song), 330, 14), 14),
                    toga.Box(
                        children=[
                            stat(str(round(song["score"])), "SCORE", theme.GOLD),
                            stat(str(song["matches"]), "VOTES"),
                            stat(rank_label(rank), "RANK", color),
                        ],
                        style=theme.row(gap=8, margin=(8, 0, 0, 0)),
                    ),
                    padding=16,
                    gap=8,
                    stroke=color if rank <= len(theme.MEDALS) else theme.BORDER,
                ),
                theme.pill("⇄  Merge with another song…", self.merge, "surface", 48),
                theme.pill("✕  Delete song", self.delete, "danger", 48),
                back_button(controller, "songs"),
            ],
            style=theme.page(),
        )

    def refresh(self):
        pass

    def merge(self, widget, **kw):
        self.c.show_screen(MergeForm(self.c, self.key))

    async def delete(self, widget, **kw):
        song = self.c.session.songs.get(self.key)
        if song and await self.c.confirm("Delete Song", f"Remove '{song['title']}' from the session?"):
            self.c.session.delete_songs([self.key])
            self.c.songs_changed(f"Deleted '{song['title']}'.", screen="songs")


class AlbumsScreen:
    """Albums ranked by the average score of their songs. Tap one for options."""

    def __init__(self, controller):
        self.c = controller
        self.rows = toga.Box(style=Pack(direction=COLUMN, gap=6))
        self.box = toga.Box(
            children=[
                header("◉  Album Rankings", "Ranked by the average score of their songs"),
                scroller(self.rows),
            ],
            style=theme.page(),
        )

    def refresh(self):
        rows = [self._row(rank, a) for rank, a in enumerate(self.c.session.album_stats(), start=1)]
        self.rows.clear()
        self.rows.add(column_of(rows))

    def _row(self, rank, a):
        cover = toga.ImageView(style=Pack(width=60, height=60))
        theme.skin(cover, fill=theme.SURFACE_HI, radius=8)
        self.c.covers.show(cover, a["cover_url"])
        color = rank_color(rank)
        info = toga.Box(
            children=[
                toga.Label(theme.wrap(a["album"], 170, 15), style=theme.text(15, color, font_weight=BOLD)),
                theme.muted(theme.wrap(f"{a['artist']} · {a['count']} songs", 170, 12), 12),
            ],
            style=Pack(direction=COLUMN, flex=1, gap=2),
        )
        score = toga.Box(
            children=[
                toga.Label(f"{a['avg']:.0f}", style=theme.heading(17, theme.GOLD, text_align=RIGHT)),
                theme.muted("avg", 11, text_align=RIGHT),
            ],
            style=Pack(direction=COLUMN, width=48),
        )
        rank_text = toga.Label(
            rank_label(rank), style=theme.text(14, rank_color(rank, theme.MUTED), font_weight=BOLD, width=40)
        )
        return tappable_row(
            [rank_text, cover, info, score], lambda: self.c.show_screen(AlbumSheet(self.c, a, rank)), rank
        )


class AlbumSheet:
    """One album: battle only its songs, or remove it."""

    def __init__(self, controller, album, rank):
        self.c = controller
        self.album = album["album"]
        cover = toga.ImageView(style=Pack(width=140, height=140))
        theme.skin(cover, fill=theme.SURFACE_HI, radius=12)
        controller.covers.show(cover, album["cover_url"])
        color = rank_color(rank)
        self.box = toga.Box(
            children=[
                theme.card(
                    toga.Box(
                        children=[
                            cover,
                            toga.Box(
                                children=[
                                    theme.corner_tag(f"RANK #{rank}", color),
                                    toga.Label(
                                        theme.wrap(album["album"], 170, 20),
                                        style=theme.heading(20, theme.TEXT),
                                    ),
                                    theme.muted(theme.wrap(album["artist"], 170, 14), 14),
                                ],
                                style=Pack(direction=COLUMN, flex=1, gap=6),
                            ),
                        ],
                        style=theme.row(gap=14),
                    ),
                    toga.Box(
                        children=[
                            stat(f"{album['avg']:.0f}", "AVG SCORE", theme.GOLD),
                            stat(str(album["count"]), "SONGS"),
                        ],
                        style=theme.row(gap=8, margin=(8, 0, 0, 0)),
                    ),
                    padding=16,
                    stroke=color if rank <= len(theme.MEDALS) else theme.BORDER,
                ),
                theme.pill("⚔  Battle this album", self.battle, "gold", 50),
                theme.pill("✕  Delete album", self.delete, "danger", 48),
                back_button(controller, "albums"),
            ],
            style=theme.page(),
        )

    def refresh(self):
        pass

    def battle(self, widget, **kw):
        self.c.set_filter(self.album)
        self.c.show("battle")

    async def delete(self, widget, **kw):
        count = sum(1 for s in self.c.session.songs.values() if s["album"] == self.album)
        if await self.c.confirm("Delete Album", f"Delete all {count} songs of '{self.album}'?"):
            removed = self.c.session.delete_album(self.album)
            self.c.songs_changed(f"Deleted '{self.album}' ({removed} songs).", screen="albums")


def field(label, widget):
    return toga.Box(
        children=[theme.corner_tag(label.upper(), theme.MUTED, 10), widget],
        style=Pack(direction=COLUMN, gap=4),
    )


def form_buttons(ok_text, on_ok, on_cancel):
    return toga.Box(
        children=[
            theme.pill("Cancel", on_cancel, "ghost", 48, flex=1),
            theme.pill(ok_text, on_ok, "gold", 48, flex=1),
        ],
        style=theme.row(gap=10),
    )


class AddSongForm:
    """Enter a song by hand (for tracks MusicBrainz doesn't list)."""

    def __init__(self, controller):
        self.c = controller
        s = controller.session
        keys = s.get_filtered_keys()
        album = s.active_filter if s.active_filter != ALL_ALBUMS else ""
        self.title = theme.text_input(placeholder="Song title")
        self.artist = theme.text_input(value=s.songs[keys[0]]["artist"] if keys else "")
        self.album = theme.text_input(value=album, placeholder="Album (Year)")
        self.year = theme.text_input(placeholder="YYYY")
        self.box = toga.Box(
            children=[
                header("＋  Add a Song", "For tracks MusicBrainz doesn't list"),
                theme.card(
                    field("Title", self.title),
                    field("Artist", self.artist),
                    field("Album", self.album),
                    field("Year", self.year),
                    padding=16,
                    gap=14,
                ),
                form_buttons("Add Song", self.submit, lambda w, **kw: controller.show("songs")),
            ],
            style=theme.page(),
        )

    def refresh(self):
        pass

    async def submit(self, widget, **kw):
        title = self.title.value.strip()
        if not title:
            await self.c.info("Add Song", "Please enter a title.")
            return
        key = self.c.session.add_song(
            title, self.artist.value.strip(), self.album.value.strip(), self.year.value.strip()[:4]
        )
        if key is None:
            await self.c.info("Add Song", "That song already exists!")
            return
        self.c.songs_changed(f"Added '{title}'.", screen="songs")


class MergeForm:
    """Combine a song with another one (duplicates, alternate titles)."""

    def __init__(self, controller, key):
        self.c = controller
        self.key = key
        s = controller.session
        song = s.songs[key]
        others = sorted((k for k in s.songs if k != key), key=lambda k: s.songs[k]["title"].casefold())
        self.other = toga.Selection(
            items=[{"name": f"{s.songs[k]['title']} ({s.songs[k]['album']})", "key": k} for k in others],
            accessor="name",
            style=Pack(color=theme.TEXT),
        )
        device.tint(self.other, theme.MUTED)
        self.new_title = theme.text_input(value=song["title"])
        self.box = toga.Box(
            children=[
                header(
                    "⇄  Merge Songs",
                    f"Combine '{song['title']}' with another song. Scores are averaged and votes added up.",
                ),
                theme.card(
                    field("Merge with", self.other),
                    field("Title of the merged song", self.new_title),
                    padding=16,
                    gap=14,
                ),
                form_buttons("Merge", self.submit, lambda w, **kw: controller.show("songs")),
            ],
            style=theme.page(),
        )

    def refresh(self):
        pass

    async def submit(self, widget, **kw):
        new_title = self.new_title.value.strip()
        if self.other.value is None or not new_title:
            await self.c.info("Merge", "Pick a song and enter a title.")
            return
        if self.c.session.merge_into([self.key, self.other.value.key], new_title) is None:
            await self.c.info("Merge", "Another song already has that title!")
            return
        self.c.songs_changed(f"Merged into '{new_title}'.", screen="songs")
