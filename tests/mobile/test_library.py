import os

from songclash.core.models import normalize_song
from songclash.core.storage import write_session
from songclash.mobile.library import SessionLibrary, safe_name


def _songs(n):
    return {f"A — s{i}": normalize_song(f"s{i}", {"artist": "A"}) for i in range(n)}


def test_safe_name():
    assert safe_name("AC/DC") == "AC-DC"
    assert safe_name('  "What?"  ') == "What"
    assert safe_name("...") == "Session"


def test_new_path_avoids_clashes(tmp_path):
    lib = SessionLibrary(tmp_path)
    first = lib.new_path("Blur")
    first.write_text("{}")
    assert lib.new_path("Blur").name == "Blur (2).json"


def test_sessions_sorted_and_skip_broken(tmp_path):
    lib = SessionLibrary(tmp_path)
    old, new = lib.sessions_dir / "old.json", lib.sessions_dir / "new.json"
    write_session(old, _songs(2))
    write_session(new, _songs(3))
    os.utime(old, (1, 1))
    (lib.sessions_dir / "broken.json").write_text("not json")
    infos = lib.sessions()
    assert [(i.name, i.songs) for i in infos] == [("new", 3), ("old", 2)]


def test_rename_and_last_session(tmp_path):
    lib = SessionLibrary(tmp_path)
    path = lib.new_path("x")
    write_session(path, _songs(1))
    lib.set_last_session(path)
    assert lib.last_session() == path
    renamed = lib.rename(path, "Better Name")
    assert renamed.name == "Better Name.json" and not path.exists()
    assert lib.last_session() is None  # the old file is gone
    lib.delete(renamed)
    assert lib.sessions() == []


def test_settings_roundtrip(tmp_path):
    lib = SessionLibrary(tmp_path)
    assert lib.settings() == {}
    lib.update_settings(import_types=["EP"])
    lib.update_settings(last_session="a.json")
    assert SessionLibrary(tmp_path).settings() == {"import_types": ["EP"], "last_session": "a.json"}
