"""30-second previews: iTunes lookup, playback, and the per-side state."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import requests

from songclash.mobile.device import make_player
from songclash.services import itunes

IDLE, LOADING, PLAYING, MISSING = "idle", "loading", "playing", "missing"


class PreviewController:
    """Plays one preview at a time for side "A" or "B".

    ``on_state(side, state)`` updates the buttons; ``on_message(text)`` shows
    errors. Found preview URLs are cached on the song so they get saved.
    """

    def __init__(self, on_state: Callable[[str, str], None], on_message: Callable[[str], None]):
        self.on_state = on_state
        self.on_message = on_message
        self.player = make_player()
        self.active_side: str | None = None
        self.pending: tuple[str, str] | None = None  # (song key, side) being looked up
        self.no_preview: set[str] = set()

    def toggle(self, side, key, song):
        if self.active_side == side:
            self.stop()
            return
        if not song or self.pending == (key, side):
            return
        if song.get("preview_url"):
            self._play(side, song["preview_url"])
        elif key in self.no_preview:
            self._flash_missing(side)
        else:
            asyncio.ensure_future(self._lookup(side, key, song))

    async def _lookup(self, side, key, song):
        self.stop()
        self.pending = (key, side)
        self.on_state(side, LOADING)
        loop = asyncio.get_running_loop()
        try:
            url = await loop.run_in_executor(
                None, itunes.find_preview, song["artist"], song["title"], song["album"]
            )
        except requests.RequestException as e:
            if self.pending == (key, side):
                self.pending = None
                self.on_state(side, IDLE)
                self.on_message(f"Preview lookup failed: {e}")
            return
        if url:
            song["preview_url"] = url
        else:
            self.no_preview.add(key)
        # stop() clears pending when the matchup changes: drop stale results
        if self.pending != (key, side):
            return
        self.pending = None
        if url:
            self._play(side, url)
        else:
            self._flash_missing(side)

    def _flash_missing(self, side):
        self.on_state(side, MISSING)
        self.on_message("No preview available for this song.")

        async def reset():
            await asyncio.sleep(2)
            if self.active_side != side and self.pending is None:
                self.on_state(side, IDLE)

        asyncio.ensure_future(reset())

    def _play(self, side, url):
        self.stop()
        self.active_side = side
        self.on_state(side, LOADING)

        def started():
            if self.active_side == side:
                self.on_state(side, PLAYING)

        def finished(error):
            if self.active_side == side:
                self.active_side = None
                self.on_state(side, IDLE)
            if error:
                self.on_message(error)

        self.player.play(url, started, finished)

    def progress(self) -> float:
        return self.player.progress() if self.active_side else 0.0

    def stop(self):
        self.player.stop()
        self.pending = None
        previous, self.active_side = self.active_side, None
        for side in ("A", "B"):
            self.on_state(side, IDLE)
        return previous

    def forget_misses(self):
        self.no_preview.clear()
