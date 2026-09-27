"""The "Add Artist" flow: search, pick the artist, choose release types, fetch."""

from __future__ import annotations

import asyncio
import functools
import threading

import requests
import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from songclash.mobile import theme
from songclash.services import musicbrainz
from songclash.services.errors import FetchCancelled, FetchError


def artist_details(a: dict) -> str:
    return ", ".join(x for x in (a["disambiguation"], a["type"], a["country"], a["begin"]) if x)


class ImportScreen:
    """One screen whose body changes with each step of the import."""

    def __init__(self, controller):
        self.c = controller
        self.cancel_event: threading.Event | None = None
        self.query = toga.TextInput(placeholder="Artist name", on_confirm=self.search, style=Pack(flex=1))
        self.btn_search = toga.Button(
            "Search",
            on_press=self.search,
            style=theme.button(color=theme.GOLD, text_color=theme.BG, width=100),
        )
        self.body = toga.Box(style=Pack(direction=COLUMN, gap=8))
        self.box = toga.Box(
            children=[
                toga.Label("＋ Add an Artist", style=theme.heading(18)),
                toga.Box(children=[self.query, self.btn_search], style=theme.row(gap=8)),
                toga.ScrollContainer(content=self.body, horizontal=False, style=Pack(flex=1)),
            ],
            style=theme.page(),
        )

    def refresh(self):
        if self.cancel_event is None:  # don't interrupt a running import
            self._set_body(
                toga.Label(
                    "Songs come from MusicBrainz. Studio albums are included by default; "
                    "you can add EPs, live albums and more in the next step.",
                    style=theme.text(13, theme.MUTED),
                )
            )

    def _set_body(self, *widgets):
        self.body.clear()
        for w in widgets:
            self.body.add(w)

    def _busy(self, busy: bool):
        self.query.enabled = not busy
        self.btn_search.enabled = not busy

    # ---------- Step 1: search ----------

    async def search(self, widget, **kw):
        name = self.query.value.strip()
        if not name or self.cancel_event is not None:
            return
        self._busy(True)
        self._set_body(toga.Label(f"Searching MusicBrainz for '{name}'…", style=theme.text()))
        try:
            loop = asyncio.get_running_loop()
            artists = await loop.run_in_executor(None, musicbrainz.search_artists, name)
        except (FetchError, requests.RequestException) as e:
            self.refresh()
            await self.c.info("Search Failed", str(e))
            return
        finally:
            self._busy(False)
        self.show_artists(name, artists)

    # ---------- Step 2: pick the artist ----------

    def show_artists(self, query, artists):
        if not artists:
            self._set_body(toga.Label(f"No artist found for '{query}'.", style=theme.text()))
            return
        exact = [a for a in artists if a["name"].casefold() == query.casefold()]
        if len(exact) == 1:
            self.show_options(exact[0])
            return
        buttons = [toga.Label("Several artists match. Which one did you mean?", style=theme.text())]
        for a in artists:
            details = artist_details(a)
            label = f"{a['name']}\n{details}" if details else a["name"]
            buttons.append(
                toga.Button(
                    label,
                    on_press=functools.partial(lambda a, w, **kw: self.show_options(a), a),
                    style=theme.button(height=64, font_size=14),
                )
            )
        self._set_body(*buttons)

    # ---------- Step 3: release types ----------

    def show_options(self, artist):
        checked = set(self.c.library.settings().get("import_types", []))
        switches = {
            name: toga.Switch(name, value=name in checked, style=theme.text(15))
            for name in musicbrainz.IMPORT_OPTIONS
        }

        async def start(widget, **kw):
            chosen = [name for name, sw in switches.items() if sw.value]
            self.c.library.update_settings(import_types=chosen)
            await self.fetch(artist, chosen)

        details = artist_details(artist)
        self._set_body(
            toga.Label(artist["name"], style=theme.heading(20, theme.TEXT)),
            *([toga.Label(details, style=theme.text(12, theme.MUTED))] if details else []),
            toga.Label("Studio albums are always included. Also include:", style=theme.text()),
            *switches.values(),
            toga.Button(
                "Import Songs",
                on_press=start,
                style=theme.button(color=theme.GOLD, text_color=theme.BG, height=56),
            ),
        )

    # ---------- Step 4: fetch ----------

    async def fetch(self, artist, checked):
        loop = asyncio.get_running_loop()
        self.cancel_event = threading.Event()
        label = toga.Label(f"Fetching songs for {artist['name']}…", style=theme.text())
        bar = toga.ProgressBar(max=None)
        bar.start()
        cancel = toga.Button("Cancel", on_press=lambda w, **kw: self.cancel_event.set(), style=theme.button())
        self._set_body(label, bar, cancel)
        self._busy(True)

        def update(msg, pct):
            label.text = msg
            if pct < 0:
                bar.max = None
                bar.start()
            else:
                bar.stop()
                bar.max = 100
                bar.value = pct

        def progress(msg, pct):  # called on the worker thread
            loop.call_soon_threadsafe(update, msg, pct)

        fetch = functools.partial(
            musicbrainz.fetch_discography,
            artist["id"],
            artist["name"],
            progress=progress,
            cancel=self.cancel_event,
            **musicbrainz.discography_options(checked),
        )
        try:
            songs = await loop.run_in_executor(None, fetch)
        except FetchCancelled:
            songs = None
        except (FetchError, requests.RequestException) as e:
            songs = None
            await self.c.info("Fetch Failed", str(e))
        finally:
            bar.stop()
            self.cancel_event = None
            self._busy(False)
            self.refresh()
        if songs is not None:
            self.query.value = ""
            await self.c.artist_imported(artist["name"], songs)
