import random

from songclash.core.matchmaking import pair_id, pick_matchup
from songclash.core.models import normalize_song


def make_songs(n, matches=0):
    return {f"k{i}": normalize_song(f"S{i}", {"matches": matches}) for i in range(n)}


def test_needs_two_candidates():
    songs = make_songs(1)
    assert pick_matchup(songs, list(songs)) is None


def test_returns_two_distinct_candidates():
    songs = make_songs(6)
    for seed in range(20):
        a, b = pick_matchup(songs, ["k1", "k3", "k5"], rng=random.Random(seed))
        assert a != b
        assert {a, b} <= {"k1", "k3", "k5"}


def test_prefers_least_played_song():
    songs = make_songs(8, matches=10)
    songs["k7"]["matches"] = 0
    songs["k6"]["matches"] = 0
    for seed in range(20):
        pair = pick_matchup(songs, list(songs), rng=random.Random(seed))
        assert {"k6", "k7"} & set(pair)


def test_avoids_recent_pairs_when_possible():
    songs = make_songs(3)
    recent = {pair_id("k0", "k1"), pair_id("k0", "k2"), pair_id("k1", "k2")}
    # Every pair is recent, so it falls back to any opponent
    assert pick_matchup(songs, list(songs), recent, rng=random.Random(0)) is not None

    # k0 is well played, so song A is k1 or k2; k0 is only a recent opponent
    songs["k0"]["matches"] = 10
    recent = {pair_id("k0", "k1"), pair_id("k0", "k2")}
    for seed in range(20):
        pair = pick_matchup(songs, list(songs), recent, rng=random.Random(seed))
        assert set(pair) == {"k1", "k2"}


def test_pair_id_is_order_independent():
    assert pair_id("b", "a") == pair_id("a", "b") == ("a", "b")
