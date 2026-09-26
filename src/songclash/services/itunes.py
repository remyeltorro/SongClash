"""iTunes Search: 30-second audio previews."""

from __future__ import annotations

import re

import requests

from songclash.services.titles import alnum_key, normalize_title, strip_brackets

SEARCH_URL = "https://itunes.apple.com/search"
_ALBUM_YEAR_RE = re.compile(r"\s*\(\d{4}\)$")


def _search(term: str) -> list[dict]:
    resp = requests.get(
        SEARCH_URL,
        params={"term": term, "media": "music", "entity": "song", "limit": 10},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _overlaps(a: str, b: str) -> bool:
    return a in b or b in a


def find_preview(artist: str, title: str, album: str = "") -> str:
    """Return an iTunes 30s preview URL, or "" if there is no matching song.

    Raises requests.RequestException on network errors so callers can tell
    "not found" apart from "couldn't check".
    """
    target_artist, target_title = alnum_key(artist), alnum_key(normalize_title(title))
    target_album = alnum_key(_ALBUM_YEAR_RE.sub("", album))

    # iTunes finds nothing for some long titles ("Backdrifts. (Honeymoon Is
    # Over.)"), so fall back to the title without any bracketed part.
    short_title = strip_brackets(title)
    terms = [f"{artist} {title}"]
    if short_title and short_title != title:
        terms.append(f"{artist} {short_title}")

    for term in terms:
        best = None
        for r in _search(term):
            r_artist = alnum_key(r.get("artistName", ""))
            r_track = alnum_key(normalize_title(r.get("trackName", "")))
            r_album = alnum_key(r.get("collectionName", ""))
            if not r.get("previewUrl") or not r_artist or not r_track:
                continue
            if not _overlaps(target_artist, r_artist) or not _overlaps(target_title, r_track):
                continue
            if target_album and _overlaps(target_album, r_album):
                return r["previewUrl"]  # artist, title and album all match
            best = best or r
        if best:
            return best["previewUrl"]
    return ""
