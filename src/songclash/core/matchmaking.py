"""Choosing which two songs battle next."""

from __future__ import annotations

import random
from collections.abc import Container, Mapping

from songclash.core.models import Song

Pair = tuple[str, str]


def pair_id(a: str, b: str) -> Pair:
    """Order-independent id of a pairing, for the recent-match history."""
    return (a, b) if a <= b else (b, a)


def pick_matchup(
    songs: Mapping[str, Song],
    candidates: list[str],
    recent: Container[Pair] = (),
    rng: random.Random | None = None,
) -> list[str] | None:
    """Pick two keys from ``candidates``, or None if there are fewer than two.

    - Coverage: song A comes from the least-played quarter, so every song
      gets rated.
    - Fair fights: song B is weighted towards a similar rating (a closer,
      more informative comparison), skipping pairs in ``recent``.
    """
    rng = rng or random
    if len(candidates) < 2:
        return None
    candidates = list(candidates)

    rng.shuffle(candidates)
    candidates.sort(key=lambda k: songs[k]["matches"])
    pool_size = max(2, len(candidates) // 4)
    song_a = rng.choice(candidates[:pool_size])
    score_a = songs[song_a]["score"]

    opponents, weights = [], []
    for opp in candidates:
        if opp == song_a or pair_id(song_a, opp) in recent:
            continue
        opponents.append(opp)
        weights.append(1000 / (abs(score_a - songs[opp]["score"]) + 50))
    if not opponents:
        opponents = [k for k in candidates if k != song_a]
        weights = [1] * len(opponents)

    song_b = rng.choices(opponents, weights=weights, k=1)[0]
    pair = [song_a, song_b]
    rng.shuffle(pair)
    return pair
