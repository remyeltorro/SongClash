"""Domain logic: songs, Elo scoring, matchmaking, persistence.

Nothing in this package may import Qt or do network I/O, so it can be unit
tested directly and reused by other front ends.
"""

from songclash.core.models import INITIAL_SCORE, Song, normalize_song, song_key
from songclash.core.session import ALL_ALBUMS, RankingSession

__all__ = ["ALL_ALBUMS", "INITIAL_SCORE", "RankingSession", "Song", "normalize_song", "song_key"]
