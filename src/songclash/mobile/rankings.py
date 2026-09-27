"""Song and album leaderboards, plus the add-song and merge forms."""

from __future__ import annotations

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, RIGHT

from songclash.core.export import ranking_csv
from songclash.core.session import ALL_ALBUMS
from songclash.mobile import theme
from songclash.mobile.library import safe_name


def rank_label(rank: int) -> str:
    return f"{theme.MEDALS[rank - 1]} {rank}" if rank <= len(theme.MEDALS) else str(rank)


class SongsScreen:
    """Ranked songs for the current album filter. Long-press a song to edit it."""

    def __init__(self, controller):
        self.c = controller
        self.title = toga.Label("", style=theme.heading(18))
        self.hint = toga.Label("Long-press a song to delete or merge it.", style=theme.text(12, theme.MUTED))
        self.list = toga.DetailedList(
            accessors=("title", "subtitle", "icon"),
            primary_action="Delete",
            on_primary_action=self.delete_song,
            secondary_action="Merge with…",
            on_secondary_action=self.merge_song,
            style=Pack(flex=1),
        )
        buttons = toga.Box(
            children=[
                theme.Button("＋ Add Song", on_press=self.add_song, style=theme.button(flex=1)),
                theme.Button(
                    "Export CSV",
                    on_press=self.export_csv,
                    style=theme.button(color=theme.GOLD, text_color=theme.BG, flex=1),
                ),
            ],
            style=theme.row(gap=8),
        )
        self.box = toga.Box(children=[self.title, buttons, self.hint, self.list], style=theme.page())

    def refresh(self):
        s = self.c.session
        self.title.text = theme.wrap(f"♛ Leaderboard · {s.active_filter}", size=18)
        rows = []
        for rank, key in enumerate(s.ranked_keys(), start=1):
            song = s.songs[key]
            rows.append(
                {
                    "title": f"{rank_label(rank)}.  {song['title']}",
                    "subtitle": f"{round(song['score'])} pts · {song['matches']} votes · {song['album']}",
                    "icon": None,
                    "key": key,
                }
            )
        self.list.data = rows

    async def delete_song(self, widget, row, **kw):
        song = self.c.session.songs.get(row.key)
        if song and await self.c.confirm("Delete Song", f"Remove '{song['title']}' from the session?"):
            self.c.session.delete_songs([row.key])
            self.c.songs_changed(f"Deleted '{song['title']}'.")

    def merge_song(self, widget, row, **kw):
        if row.key in self.c.session.songs:
            self.c.show_screen(MergeForm(self.c, row.key))

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


class AlbumsScreen:
    """Albums ranked by the average score of their songs."""

    def __init__(self, controller):
        self.c = controller
        self.rows = toga.Box(style=Pack(direction=COLUMN, gap=8))
        self.box = toga.Box(
            children=[
                toga.Label("◉ Album Rankings", style=theme.heading(18)),
                toga.ScrollContainer(content=self.rows, horizontal=False, style=Pack(flex=1)),
            ],
            style=theme.page(),
        )

    def refresh(self):
        self.rows.clear()
        for rank, a in enumerate(self.c.session.album_stats(), start=1):
            cover = toga.ImageView(style=Pack(width=60, height=60, background_color=theme.SURFACE_HI))
            self.c.covers.show(cover, a["cover_url"])
            color = theme.GOLD if rank <= len(theme.MEDALS) else theme.TEXT
            info = toga.Box(
                children=[
                    toga.Label(theme.wrap(a["album"], 180, 15), style=theme.text(15, color)),
                    toga.Label(
                        theme.wrap(f"{a['artist']} · {a['count']} songs", 180, 12),
                        style=theme.text(12, theme.MUTED),
                    ),
                ],
                style=Pack(direction=COLUMN, flex=1),
            )
            self.rows.add(
                toga.Box(
                    children=[
                        toga.Label(rank_label(rank), style=theme.text(14, color, width=44)),
                        cover,
                        info,
                        toga.Label(f"{a['avg']:.0f}", style=theme.text(15, theme.GOLD, text_align=RIGHT)),
                    ],
                    style=theme.row(gap=10, background_color=theme.SURFACE, margin=6),
                )
            )


def _field(label, widget):
    return toga.Box(
        children=[toga.Label(label, style=theme.text(13, theme.MUTED)), widget],
        style=Pack(direction=COLUMN, gap=4),
    )


def _form_buttons(ok_text, on_ok, on_cancel):
    return toga.Box(
        children=[
            theme.Button("Cancel", on_press=on_cancel, style=theme.button(flex=1)),
            theme.Button(
                ok_text, on_press=on_ok, style=theme.button(color=theme.GOLD, text_color=theme.BG, flex=1)
            ),
        ],
        style=theme.row(gap=8),
    )


class AddSongForm:
    """Enter a song by hand (for tracks MusicBrainz doesn't list)."""

    def __init__(self, controller):
        self.c = controller
        s = controller.session
        keys = s.get_filtered_keys()
        album = s.active_filter if s.active_filter != ALL_ALBUMS else ""
        self.title = toga.TextInput(placeholder="Song title")
        self.artist = toga.TextInput(value=s.songs[keys[0]]["artist"] if keys else "")
        self.album = toga.TextInput(value=album, placeholder="Album (Year)")
        self.year = toga.TextInput(placeholder="YYYY")
        self.box = toga.Box(
            children=[
                toga.Label("Add a Song", style=theme.heading(18)),
                _field("Title", self.title),
                _field("Artist", self.artist),
                _field("Album", self.album),
                _field("Year", self.year),
                _form_buttons("Add Song", self.submit, lambda w, **kw: controller.show("songs")),
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
        )
        self.new_title = toga.TextInput(value=song["title"])
        self.box = toga.Box(
            children=[
                toga.Label("Merge Songs", style=theme.heading(18)),
                toga.Label(
                    theme.wrap(
                        f"Combine '{song['title']}' with another song. "
                        "Scores are averaged and votes added up.",
                        size=13,
                    ),
                    style=theme.text(13, theme.MUTED),
                ),
                _field("Merge with", self.other),
                _field("Title of the merged song", self.new_title),
                _form_buttons("Merge", self.submit, lambda w, **kw: controller.show("songs")),
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
