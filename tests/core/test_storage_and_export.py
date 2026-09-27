import csv

from songclash.core.export import CSV_HEADER, ranking_csv, write_ranking_csv
from songclash.core.models import normalize_song
from songclash.core.storage import dumps_session, loads_session, read_session, write_session


def test_write_is_atomic_and_roundtrips(tmp_path):
    songs = {"A — x": normalize_song("x", {"artist": "A", "album": "Ü (1999)"})}
    path = tmp_path / "s.json"
    write_session(path, songs)
    assert not (tmp_path / "s.json.tmp").exists()
    assert read_session(path) == songs


def test_csv_export(tmp_path):
    songs = [
        normalize_song("Best", {"artist": "A", "album": "X", "year": "2001", "score": 1260.6}),
        normalize_song("Worst", {"artist": "A", "album": "X", "year": "2001", "score": 1140}),
    ]
    path = tmp_path / "out.csv"
    assert write_ranking_csv(path, songs) == 2
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == CSV_HEADER
    assert rows[1] == ["Best", "A", "X", "2001", "1", "1261"]
    assert rows[2][4] == "2"


def test_session_text_roundtrip_accepts_bom():
    songs = {"A — x": normalize_song("x", {"artist": "A"})}
    assert loads_session(("﻿" + dumps_session(songs)).encode("utf-8")) == songs


def test_ranking_csv_text():
    text = ranking_csv([normalize_song("a, b", {"artist": "A"})])
    assert text.splitlines()[1].startswith('"a, b",A,')
