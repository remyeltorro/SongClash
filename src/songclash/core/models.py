"""The song record shared by every layer, and helpers to build it."""

from __future__ import annotations

from typing import Any, TypedDict

INITIAL_SCORE = 1200.0


class Song(TypedDict, total=False):
    """One song in a session. This is also the on-disk JSON shape.

    Adding a field: give it a default in ``normalize_song`` so older session
    files keep loading.
    """

    title: str
    artist: str
    album: str  # "Title (Year)"; the year disambiguates same-named albums
    year: str  # four digits, or "????" when unknown
    score: float  # Elo rating
    matches: int  # number of votes this song took part in
    cover_url: str | None
    preview_url: str  # cached iTunes preview, filled lazily


def song_key(artist: str, title: str) -> str:
    """Unique id for a song. Titles alone collide across artists ("Intro")."""
    return f"{artist} — {title}"


def normalize_song(title: str, data: Any) -> Song:
    """Fill in missing fields so older or hand-edited files still load."""
    song = dict(data) if isinstance(data, dict) else {}
    song.setdefault("title", title)
    song["artist"] = song.get("artist") or "Unknown Artist"
    song["album"] = song.get("album") or "Unknown Album"
    song["year"] = str(song.get("year") or "????")
    song["score"] = float(song.get("score", INITIAL_SCORE))
    song["matches"] = int(song.get("matches", 0))
    song.setdefault("cover_url", None)
    return song  # type: ignore[return-value]


def song_caption(song: Song) -> str:
    """ "Artist · Album (Year)", without repeating a year already in the album."""
    album = song["album"]
    if song["year"] not in album:
        album = f"{album} ({song['year']})"
    return f"{song['artist']} · {album}"
