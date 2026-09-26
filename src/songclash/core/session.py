"""Ranking session: the song database, voting, undo and editing."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from songclash.core import elo, storage
from songclash.core.matchmaking import pair_id, pick_matchup
from songclash.core.models import Song, normalize_song, song_key

ALL_ALBUMS = "All Albums"


class RankingSession:
    """All songs being ranked, plus per-session state (filter, undo, file).

    Pure Python: the UI reads and mutates it, then refreshes itself.
    """

    MATCH_HISTORY = 20  # recent pairings to avoid repeating
    UNDO_DEPTH = 200

    def __init__(self):
        self.new_session()

    def new_session(self):
        self.songs: dict[str, Song] = {}
        self.current_filename: str | None = None
        self.has_unsaved_changes = False
        self.active_filter = ALL_ALBUMS
        self.match_history: deque[tuple[str, str]] = deque(maxlen=self.MATCH_HISTORY)
        self.undo_stack: deque[tuple[str, str, float, float]] = deque(maxlen=self.UNDO_DEPTH)
        self.votes_this_session = 0

    # ---------- Persistence ----------

    def load_from_file(self, filepath: str) -> int:
        """Load a session. Raises OSError/ValueError on failure."""
        songs = storage.read_session(filepath)
        self.new_session()
        self.songs = songs
        self.current_filename = filepath
        return len(songs)

    def save_session(self, filepath: str | None = None):
        target = filepath or self.current_filename
        if not target:
            raise ValueError("No filename specified")
        storage.write_session(target, self.songs)
        self.current_filename = target
        self.has_unsaved_changes = False

    def merge_file(self, filepath: str) -> int:
        return self.merge_songs(storage.read_session(filepath))

    def merge_songs(self, songs: dict[str, Song]) -> int:
        """Add songs ({key: song}) that aren't already in the session."""
        added = 0
        for key, song in songs.items():
            if key not in self.songs:
                self.songs[key] = song
                added += 1
        if added:
            self.has_unsaved_changes = True
        return added

    def add_fetched_songs(self, fetched: Iterable[dict]) -> int:
        """Merge the song dicts returned by the MusicBrainz service."""
        return self.merge_songs(
            {song_key(s["artist"], s["title"]): normalize_song(s["title"], s) for s in fetched}
        )

    # ---------- Editing ----------

    def add_song(self, title: str, artist: str = "", album: str = "", year: str = "") -> str | None:
        """Add a manual song. Returns its key, or None if it already exists."""
        song = normalize_song(title, {"artist": artist, "album": album, "year": year})
        key = song_key(song["artist"], title)
        if key in self.songs:
            return None
        self.songs[key] = song
        self._structure_changed()
        return key

    def delete_songs(self, keys: Iterable[str]) -> int:
        count = 0
        for k in keys:
            if self.songs.pop(k, None) is not None:
                count += 1
        if count:
            self._structure_changed()
        return count

    def delete_album(self, album: str) -> int:
        return self.delete_songs([k for k, s in self.songs.items() if s["album"] == album])

    def merge_into(self, keys: list[str], new_title: str) -> str | None:
        """Combine several songs into one (averaged score, summed matches).

        Metadata comes from the first key. Returns the new key, or None if
        the resulting key would clash with an unrelated song.
        """
        first = self.songs[keys[0]]
        new_key = song_key(first["artist"], new_title)
        if new_key in self.songs and new_key not in keys:
            return None
        merged = dict(first)
        merged["title"] = new_title
        merged["score"] = sum(self.songs[k]["score"] for k in keys) / len(keys)
        merged["matches"] = sum(self.songs[k]["matches"] for k in keys)
        merged.pop("preview_url", None)
        for k in keys:
            del self.songs[k]
        self.songs[new_key] = merged
        self._structure_changed()
        return new_key

    def _structure_changed(self):
        self.has_unsaved_changes = True
        # Undo entries may reference songs that no longer exist.
        self.undo_stack.clear()
        self.match_history.clear()

    # ---------- Queries ----------

    def get_albums_list(self) -> list[str]:
        return sorted({s["album"] for s in self.songs.values()})

    def get_filtered_keys(self) -> list[str]:
        if self.active_filter == ALL_ALBUMS:
            return list(self.songs)
        return [k for k, s in self.songs.items() if s["album"] == self.active_filter]

    def ranked_keys(self, keys: list[str] | None = None) -> list[str]:
        keys = self.get_filtered_keys() if keys is None else keys
        return sorted(keys, key=lambda k: self.songs[k]["score"], reverse=True)

    def album_stats(self) -> list[dict]:
        """Per-album average score, sorted best first."""
        stats: dict[tuple[str, str], dict] = {}
        for s in self.songs.values():
            entry = stats.setdefault(
                (s["artist"], s["album"]),
                {"album": s["album"], "artist": s["artist"], "total": 0.0, "count": 0, "cover_url": None},
            )
            entry["total"] += s["score"]
            entry["count"] += 1
            entry["cover_url"] = entry["cover_url"] or s.get("cover_url")
        albums = list(stats.values())
        for a in albums:
            a["avg"] = a["total"] / a["count"]
        albums.sort(key=lambda a: a["avg"], reverse=True)
        return albums

    # ---------- Matchmaking & scoring ----------

    def get_matchup(self) -> list[str] | None:
        pair = pick_matchup(self.songs, self.get_filtered_keys(), self.match_history)
        if pair:
            self.match_history.append(pair_id(*pair))
        return pair

    def update_score(self, winner: str, loser: str):
        w, l = self.songs[winner], self.songs[loser]
        self.undo_stack.append((winner, loser, w["score"], l["score"]))

        delta = elo.rating_change(w["score"], l["score"])
        w["score"] += delta
        l["score"] -= delta
        w["matches"] += 1
        l["matches"] += 1
        self.votes_this_session += 1
        self.has_unsaved_changes = True

    def undo_last_vote(self) -> tuple[str, str] | None:
        """Revert the last vote. Returns the (winner, loser) pair, or None."""
        if not self.undo_stack:
            return None
        winner, loser, w_score, l_score = self.undo_stack.pop()
        for key, score in ((winner, w_score), (loser, l_score)):
            self.songs[key]["score"] = score
            self.songs[key]["matches"] -= 1
        self.votes_this_session -= 1
        self.has_unsaved_changes = True
        return winner, loser
