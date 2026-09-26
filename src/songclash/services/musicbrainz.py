"""MusicBrainz: artist search and discographies.

Plain blocking Python so it can run on a background thread. Long operations
accept a ``progress`` callback and a ``cancel`` event.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable

import requests

from songclash import REPO_URL, __version__
from songclash.services.errors import FetchCancelled, FetchError
from songclash.services.titles import normalize_title

MB_ROOT = "https://musicbrainz.org/ws/2"
COVER_ROOT = "https://coverartarchive.org/release-group"
# MusicBrainz requires a meaningful User-Agent
USER_AGENT = f"SongClash/{__version__} ( {REPO_URL} )"

# Release-group secondary types that can be toggled in the import dialog.
SECONDARY_TYPES = [
    "Live",
    "Compilation",
    "Remix",
    "Soundtrack",
    "Spokenword",
    "Interview",
    "Audio drama",
    "Demo",
    "Audiobook",
    "DJ-mix",
    "Mixtape/Street",
]

# MusicBrainz "special purpose" track titles that are not real songs.
_JUNK_TITLES = {"[silence]", "[data track]", "[untitled]", "[unknown]"}

Progress = Callable[[str, int], None]


class MusicBrainzClient:
    """Minimal MusicBrainz JSON client with rate limiting and retries."""

    MIN_INTERVAL = 1.1  # MusicBrainz allows ~1 request/second
    MAX_RETRIES = 5
    RETRY_STATUSES = (429, 500, 502, 503, 504)

    def __init__(self, cancel: threading.Event | None = None):
        self.cancel = cancel or threading.Event()
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self._last_request = 0.0

    def _sleep(self, seconds: float):
        # Event.wait returns early (True) when cancelled
        if self.cancel.wait(seconds):
            raise FetchCancelled()

    def get(self, endpoint: str, **params) -> dict:
        params["fmt"] = "json"
        error = ""
        for attempt in range(self.MAX_RETRIES):
            if self.cancel.is_set():
                raise FetchCancelled()
            wait = self._last_request + self.MIN_INTERVAL - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self.http.get(f"{MB_ROOT}/{endpoint}", params=params, timeout=20)
            except requests.RequestException as e:
                error = str(e)
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code not in self.RETRY_STATUSES:
                    raise FetchError(f"MusicBrainz returned HTTP {resp.status_code}")
                error = f"HTTP {resp.status_code}"
            self._sleep(2.0 * (2**attempt))
        raise FetchError(f"MusicBrainz is unreachable ({error})")

    def browse_all(self, endpoint: str, key: str, **params) -> list[dict]:
        """Fetch every page of a browse request."""
        offset = 0
        items: list[dict] = []
        while True:
            data = self.get(endpoint, limit=100, offset=offset, **params)
            page = data.get(key, [])
            items.extend(page)
            offset += len(page)
            if not page or offset >= data.get(f"{endpoint}-count", 0):
                return items


def search_artists(name: str, limit: int = 8) -> list[dict]:
    """Return candidate artists as dicts: id, name, disambiguation, etc."""
    data = MusicBrainzClient().get("artist", query=name, limit=limit)
    results = []
    for a in data.get("artists", []):
        life = a.get("life-span") or {}
        results.append(
            {
                "id": a["id"],
                "name": a["name"],
                "disambiguation": a.get("disambiguation", ""),
                "type": a.get("type") or "",
                "country": a.get("country") or "",
                "begin": (life.get("begin") or "")[:4],
                "score": a.get("score", 0),
            }
        )
    return results


def _pick_release(releases: list[dict], allow_bootlegs: bool) -> dict | None:
    """Choose the release whose tracklist represents the album (the earliest)."""
    allowed = {"Official", "Bootleg"} if allow_bootlegs else {"Official"}
    candidates = [r for r in releases if r.get("status") in allowed and r.get("media")]
    if not candidates:
        return None
    # Undated releases sort last; prefer official over bootleg on ties.
    return min(
        candidates,
        key=lambda r: (r.get("date") or "9999", r.get("status") != "Official"),
    )


def fetch_discography(
    artist_id: str,
    artist_name: str,
    include_types: Iterable[str] = (),
    include_eps: bool = False,
    include_bootlegs: bool = False,
    progress: Progress | None = None,
    cancel: threading.Event | None = None,
) -> list[dict]:
    """Fetch every unique song from an artist's albums.

    ``include_types`` lists secondary types (see SECONDARY_TYPES) to keep;
    album release groups with any other secondary type are skipped.
    ``progress(message, percent)`` is called along the way (percent -1 means
    indeterminate). Returns song dicts (title, artist, album, year, cover_url).
    """
    progress = progress or (lambda msg, pct: None)
    client = MusicBrainzClient(cancel)
    include_types = set(include_types)
    primary_types = {"Album", "EP"} if include_eps else {"Album"}

    progress(f"Listing albums by {artist_name}...", -1)
    groups = client.browse_all(
        "release-group",
        "release-groups",
        artist=artist_id,
        type="album|ep" if include_eps else "album",
    )
    groups = [
        g
        for g in groups
        if g.get("primary-type") in primary_types and set(g.get("secondary-types") or []) <= include_types
    ]
    # Process oldest first so each song is credited to its original album.
    groups.sort(key=lambda g: g.get("first-release-date") or "9999")

    songs: dict[str, dict] = {}  # normalized title -> song dict
    for i, group in enumerate(groups):
        progress(f"Fetching {group['title']} ({i + 1}/{len(groups)})", int(100 * i / len(groups)))
        releases = client.browse_all(
            "release", "releases", **{"release-group": group["id"], "inc": "recordings"}
        )
        release = _pick_release(releases, include_bootlegs)
        if release is None:
            continue

        year = (group.get("first-release-date") or release.get("date") or "")[:4] or "????"
        # Year disambiguates same-named albums (e.g. Peter Gabriel's first four).
        album = f"{group['title']} ({year})"

        # The release-group endpoint serves the album's canonical cover and is
        # more reliable than a specific release (some of which return 500s).
        has_cover = any(r.get("cover-art-archive", {}).get("front") for r in releases)
        cover_url = f"{COVER_ROOT}/{group['id']}/front-250" if has_cover else None

        for medium in release["media"]:
            for track in medium.get("tracks") or []:
                title = (track.get("recording") or {}).get("title") or track.get("title")
                if not title or title.lower() in _JUNK_TITLES:
                    continue
                norm = normalize_title(title)
                existing = songs.get(norm)
                if existing is None:
                    songs[norm] = {
                        "title": title,
                        "artist": artist_name,
                        "album": album,
                        "year": year,
                        "cover_url": cover_url,
                    }
                elif len(title) < len(existing["title"]):
                    # Keep the original album but prefer the plainest title.
                    existing["title"] = title

    progress("Done.", 100)
    return list(songs.values())
