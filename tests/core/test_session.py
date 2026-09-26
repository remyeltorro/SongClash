import json

import pytest

from songclash.core import RankingSession, song_key


def make_session(n=6, albums=("A (2000)", "B (2001)"), artist="Band"):
    s = RankingSession()
    s.add_fetched_songs(
        [
            {"title": f"Song {i}", "artist": artist, "album": albums[i % len(albums)], "year": "2000"}
            for i in range(n)
        ]
    )
    return s


def test_same_title_different_artists_do_not_collide():
    s = RankingSession()
    added = s.add_fetched_songs(
        [
            {"title": "Intro", "artist": "X", "album": "1", "year": "2000"},
            {"title": "Intro", "artist": "Y", "album": "2", "year": "2001"},
        ]
    )
    assert added == 2


def test_elo_update_is_zero_sum_and_undoable():
    s = make_session()
    a, b = list(s.songs)[:2]
    s.update_score(a, b)
    assert s.songs[a]["score"] == pytest.approx(1216)
    assert s.songs[b]["score"] == pytest.approx(1184)
    assert s.songs[a]["matches"] == s.songs[b]["matches"] == 1

    assert s.undo_last_vote() == (a, b)
    assert s.songs[a]["score"] == s.songs[b]["score"] == 1200
    assert s.songs[a]["matches"] == 0
    assert s.undo_last_vote() is None


def test_matchup_respects_filter():
    s = make_session()
    s.active_filter = "A (2000)"
    for _ in range(20):
        pair = s.get_matchup()
        assert pair[0] != pair[1]
        assert all(s.songs[k]["album"] == "A (2000)" for k in pair)


def test_matchup_needs_two_songs():
    assert make_session(n=1).get_matchup() is None


def test_save_and_load_roundtrip(tmp_path):
    s = make_session()
    s.songs[next(iter(s.songs))]["album"] = "Café ü"
    path = str(tmp_path / "s.json")
    s.save_session(path)
    assert not s.has_unsaved_changes

    t = RankingSession()
    assert t.load_from_file(path) == len(s.songs)
    assert t.songs == s.songs


def test_loads_legacy_title_keyed_files(tmp_path):
    legacy = {
        "Creep": {
            "score": 1250.5,
            "matches": 3,
            "album": "Pablo Honey (1993)",
            "year": "1993",
            "artist": "Radiohead",
        }
    }
    path = tmp_path / "old.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    s = RankingSession()
    s.load_from_file(str(path))
    song = s.songs[song_key("Radiohead", "Creep")]
    assert song["title"] == "Creep"
    assert song["score"] == 1250.5


def test_load_rejects_garbage(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[1, 2, 3]")
    with pytest.raises(ValueError):
        RankingSession().load_from_file(str(path))


def test_merge_into_combines_stats():
    s = make_session(n=2)
    k1, k2 = list(s.songs)
    s.songs[k1].update(score=1300, matches=4)
    s.songs[k2].update(score=1100, matches=2)
    new_key = s.merge_into([k1, k2], "Merged")
    assert list(s.songs) == [new_key]
    assert s.songs[new_key]["score"] == 1200
    assert s.songs[new_key]["matches"] == 6


def test_merge_into_refuses_to_overwrite_other_song():
    s = make_session(n=3)
    k1, k2, k3 = list(s.songs)
    assert s.merge_into([k1, k2], s.songs[k3]["title"]) is None
    assert len(s.songs) == 3


def test_delete_album_and_album_stats():
    s = make_session()
    assert s.delete_album("A (2000)") == 3
    stats = s.album_stats()
    assert [a["album"] for a in stats] == ["B (2001)"]
    assert stats[0]["count"] == 3


def test_structural_change_clears_undo():
    s = make_session()
    a, b = list(s.songs)[:2]
    s.update_score(a, b)
    s.delete_songs([a])
    assert s.undo_last_vote() is None
