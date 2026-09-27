"""The "Add Artist" flow: search, pick the artist, choose release types, fetch."""

from __future__ import annotations

import asyncio
import functools
import threading

import requests
import toga
from toga.style import Pack
from toga.style.pack import BOLD, COLUMN

from songclash.mobile import device, theme
from songclash.mobile.rankings import header
from songclash.services import musicbrainz
from songclash.services.errors import FetchCancelled, FetchError


def artist_details(a: dict) -> str:
    return ", ".join(x for x in (a["disambiguation"], a["type"], a["country"], a["begin"]) if x)


class ImportScreen:
    """One screen whose body changes with each step of the import."""

    def __init__(self, controller):
        self.c = controller
        self.cancel_event: threading.Event | None = None
        self.query = theme.text_input(placeholder="Artist name", on_confirm=self.search)
        self.btn_search = theme.pill("Search", self.search, "gold", 44, width=104)
        self.body = toga.Box(style=Pack(direction=COLUMN, gap=10))
        self.box = toga.Box(
            children=[
                header("＋  Add an Artist", "Import a discography from MusicBrainz"),
                theme.card(
                    toga.Box(children=[self.query, self.btn_search], style=theme.row(gap=10)),
                    padding=(8, 8, 8, 14),
                    radius=14,
                ),
                toga.ScrollContainer(
                    content=self.body, horizontal=False, style=Pack(flex=1, background_color=theme.BG)
                ),
            ],
            style=theme.page(),
        )

    def refresh(self):
        if self.cancel_event is None:  # don't interrupt a running import
            self._set_body(
                theme.muted(
                    theme.wrap(
                        "Studio albums are included by default. You can add EPs, "
                        "live albums and more in the next step.",
                        size=14,
                    ),
                    14,
                )
            )

    def _set_body(self, *widgets):
        self.body.clear()
        for w in widgets:
            self.body.add(w)

    def _busy(self, busy: bool):
        self.query.enabled = not busy
        self.btn_search.enabled = not busy

    def _status(self, text, progress=None):
        """A card with a message, and a progress bar while waiting."""
        label = toga.Label(theme.wrap(text, 340, 15), style=theme.text(15))
        children = [label]
        if progress is not None:
            device.tint(progress, theme.GOLD)
            children.append(progress)
        return theme.card(*children, padding=16, gap=12), label

    # ---------- Step 1: search ----------

    async def search(self, widget, **kw):
        name = self.query.value.strip()
        if not name or self.cancel_event is not None:
            return
        self._busy(True)
        spinner = toga.ProgressBar(max=None)
        spinner.start()
        self._set_body(self._status(f"Searching MusicBrainz for '{name}'…", spinner)[0])
        try:
            loop = asyncio.get_running_loop()
            artists = await loop.run_in_executor(None, musicbrainz.search_artists, name)
        except (FetchError, requests.RequestException) as e:
            self.refresh()
            await self.c.info("Search Failed", str(e))
            return
        finally:
            spinner.stop()
            self._busy(False)
        self.show_artists(name, artists)

    # ---------- Step 2: pick the artist ----------

    def show_artists(self, query, artists):
        if not artists:
            self._set_body(self._status(f"No artist found for '{query}'.")[0])
            return
        exact = [a for a in artists if a["name"].casefold() == query.casefold()]
        if len(exact) == 1:
            self.show_options(exact[0])
            return
        rows = [theme.corner_tag("WHICH ONE DID YOU MEAN?", theme.MUTED, 11)]
        for a in artists:
            children = [toga.Label(theme.wrap(a["name"], 320, 17), style=theme.text(17, font_weight=BOLD))]
            if details := artist_details(a):
                children.append(theme.muted(theme.wrap(details, 320, 13)))
            card = theme.card(*children, padding=(12, 16), gap=2, radius=14)
            if not device.on_tap(card, functools.partial(self.show_options, a)):
                card.children[0].add(
                    theme.pill(
                        "Choose", functools.partial(lambda a, w, **kw: self.show_options(a), a), "ghost", 36
                    )
                )
            rows.append(card)
        self._set_body(*rows)

    # ---------- Step 3: release types ----------

    def show_options(self, artist):
        checked = set(self.c.library.settings().get("import_types", []))
        switches = {name: theme.switch(name, name in checked) for name in musicbrainz.IMPORT_OPTIONS}

        async def start(widget, **kw):
            chosen = [name for name, sw in switches.items() if sw.value]
            self.c.library.update_settings(import_types=chosen)
            await self.fetch(artist, chosen)

        about = [toga.Label(theme.wrap(artist["name"], 330, 22), style=theme.heading(22, theme.TEXT))]
        if details := artist_details(artist):
            about.append(theme.muted(theme.wrap(details, 330, 13)))
        self._set_body(
            theme.card(*about, padding=16, gap=2, stroke=theme.GOLD),
            # Above the switches, so it's visible without scrolling
            theme.pill("Import Songs", start, "gold", 52, size=17),
            theme.card(
                theme.corner_tag("STUDIO ALBUMS, PLUS…", theme.MUTED, 11),
                *switches.values(),
                padding=(12, 16),
                gap=2,
            ),
        )

    # ---------- Step 4: fetch ----------

    async def fetch(self, artist, checked):
        loop = asyncio.get_running_loop()
        self.cancel_event = threading.Event()
        bar = toga.ProgressBar(max=None)
        bar.start()
        card, label = self._status(f"Fetching songs for {artist['name']}…", bar)
        cancel = theme.pill("Cancel", lambda w, **kw: self.cancel_event.set(), "ghost", 44)
        self._set_body(card, cancel)
        self._busy(True)

        def update(msg, pct):
            label.text = theme.wrap(msg, 340, 15)
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
