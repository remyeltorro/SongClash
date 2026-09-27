"""Album covers: downloaded off the UI thread, cached in memory and on disk."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import requests
import toga

from songclash.services.musicbrainz import USER_AGENT

log = logging.getLogger(__name__)


class CoverCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir) / "covers"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.images: dict[str, toga.Image | None] = {}  # None: failed this run
        self.pending: dict[str, asyncio.Task] = {}

    def _path(self, url: str) -> Path:
        return self.cache_dir / hashlib.sha1(url.encode()).hexdigest()

    def _fetch(self, url: str) -> bytes | None:
        """Blocking: disk cache, then network."""
        path = self._path(url)
        if path.is_file():
            return path.read_bytes()
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        except requests.RequestException as e:
            log.info("Cover download failed: %s", e)
            return None
        if resp.status_code != 200 or not resp.content:
            return None
        path.write_bytes(resp.content)
        return resp.content

    async def get(self, url: str) -> toga.Image | None:
        if url in self.images:
            return self.images[url]
        if url not in self.pending:
            self.pending[url] = asyncio.ensure_future(self._load(url))
        return await asyncio.shield(self.pending[url])

    async def _load(self, url):
        data = await asyncio.get_running_loop().run_in_executor(None, self._fetch, url)
        image = None
        if data:
            try:
                image = toga.Image(src=data)
            except Exception:  # not an image (an HTML error page, a truncated file)
                self._path(url).unlink(missing_ok=True)
        self.images[url] = image
        self.pending.pop(url, None)
        return image

    def show(self, view: toga.ImageView, url: str | None):
        """Put the cover for ``url`` into ``view`` as soon as it's available.

        Views are reused for the next song before slow downloads finish, so
        each view remembers which cover it currently wants.
        """
        view._wanted_cover = url
        cached = self.images.get(url) if url else None
        view.image = cached
        if url and url not in self.images:
            asyncio.ensure_future(self._show_later(view, url))

    async def _show_later(self, view, url):
        image = await self.get(url)
        if getattr(view, "_wanted_cover", None) != url:
            return
        try:
            view.image = image
        except Exception as e:  # the backend rejected the image data
            log.info("Could not show cover %s: %s", url, e)
            self.images[url] = None
