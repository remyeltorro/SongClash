"""Reading and writing session files (JSON: ``{key: Song}``)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from songclash.core.models import Song, normalize_song, song_key


def parse_session_data(raw: Any) -> dict[str, Song]:
    """Turn loaded JSON into {key: song}, migrating the old title-keyed format.

    Raises ValueError if ``raw`` isn't a session.
    """
    if not isinstance(raw, dict):
        raise ValueError("Not a SongClash session file.")
    songs = {}
    for key, data in raw.items():
        if not isinstance(data, dict):
            raise ValueError("Not a SongClash session file.")
        # Old files keyed songs by title and had no "title" field.
        song = normalize_song(key, data)
        songs[song_key(song["artist"], song["title"])] = song
    return songs


def read_session(path: str | os.PathLike) -> dict[str, Song]:
    """Load a session file. Raises OSError/ValueError on failure."""
    with open(path, encoding="utf-8") as f:
        return parse_session_data(json.load(f))


def dumps_session(songs: Mapping[str, Song]) -> str:
    """The session file contents, as text."""
    return json.dumps(songs, indent=2, ensure_ascii=False)


def loads_session(text: str | bytes) -> dict[str, Song]:
    """Parse session file contents. Raises ValueError if it isn't a session."""
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    return parse_session_data(json.loads(text))


def write_session(path: str | os.PathLike, songs: Mapping[str, Song]) -> None:
    """Save atomically so a crash mid-write can't corrupt the file."""
    tmp = f"{os.fspath(path)}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dumps_session(songs))
    os.replace(tmp, path)
