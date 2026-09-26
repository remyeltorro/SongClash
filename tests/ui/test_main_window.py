"""Offscreen smoke tests for the main window."""

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QSettings
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QLabel, QMessageBox

from songclash.core.session import ALL_ALBUMS
from songclash.ui.main_window import MainWindow
from songclash.ui.settings import AppSettings


@pytest.fixture
def window(qapp, monkeypatch):
    # Never block on a modal dialog during tests
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    qs = QSettings("SongClashTests", "SongClashTests")
    qs.clear()
    w = MainWindow(settings=AppSettings(qs))
    yield w
    w.session.has_unsaved_changes = False
    w.close()


def add_songs(w, per_album=4):
    songs = [
        {"title": f"{alb} {i}", "artist": "Band", "album": f"{alb} (2000)", "year": "2000"}
        for alb in ("Alpha", "Beta")
        for i in range(per_album)
    ]
    w.on_artist_fetched("Band", songs)


def test_starts_on_welcome_page(window):
    assert window.stack.currentWidget() is window.welcome_page


def test_voting_and_undo(window):
    add_songs(window)
    assert window.stack.currentWidget() is window.battle_page
    pair = list(window.current_pair)
    window.vote("A")
    assert window.session.songs[pair[0]]["score"] > 1200
    assert window.isWindowModified()
    window.undo_vote()
    assert window.current_pair == pair
    assert window.session.songs[pair[0]]["score"] == 1200


def test_album_label_does_not_repeat_year(window):
    add_songs(window)
    assert window.battle_page.panels["A"].caption.text().count("2000") == 1


def test_deleting_filtered_album_keeps_battle_working(window):
    """Regression: the filter used to keep pointing at the deleted album."""
    add_songs(window)
    window.battle_page.combo_filter.setCurrentText("Alpha (2000)")
    assert window.session.active_filter == "Alpha (2000)"
    window.delete_current_album()
    assert window.session.active_filter == ALL_ALBUMS
    assert window.current_pair is not None
    assert window.battle_page.panels["A"].card.isEnabled()


def test_opening_file_resets_stale_filter(window, tmp_path):
    add_songs(window)
    window.session.delete_album("Beta (2000)")
    path = str(tmp_path / "s.json")
    window.session.save_session(path)
    add_songs(window)
    window.battle_page.combo_filter.setCurrentText("Beta (2000)")
    window.open_file(path)
    assert window.session.active_filter == ALL_ALBUMS
    assert window.current_pair is not None


def test_leaderboards_refresh_live(window):
    add_songs(window)
    window.show_leaderboard()
    window.show_album_leaderboard()
    lb = window.leaderboard_win
    window.vote("A")
    assert lb.table.rowCount() == 8
    assert int(lb.table.item(0, 4).text()) > 1200
    assert window.album_win.table.rowCount() == 2
    lb.close()
    window.album_win.close()


def test_leaderboard_delete_uses_keys(window):
    add_songs(window)
    window.show_leaderboard()
    lb = window.leaderboard_win
    lb.table.selectRow(0)
    key = lb.selected_keys()[0]
    lb.delete_selected()
    assert key not in window.session.songs
    assert lb.table.rowCount() == 7
    lb.close()


def test_cover_reply_for_closed_window_is_ignored(window):
    label = QLabel()
    sip.delete(label)

    class Reply:
        def deleteLater(self):
            pass

        def error(self):
            return QNetworkReply.NetworkError.ContentNotFoundError

    reply = Reply()
    window.covers.active_downloads[reply] = ("http://x", label)
    window.covers.on_reply_finished(reply)  # must not raise


def test_stale_audio_result_is_not_played(window):
    add_songs(window)
    key = window.current_pair[0]
    song = window.session.songs[key]
    window.audio.pending = (key, "A")
    window.next_matchup()  # user moved on before the lookup finished
    played = []
    window.audio.play_url = lambda *a: played.append(a)
    window.audio.on_found(key, "A", "http://preview", song)
    assert played == []
    assert window.session.songs[key]["preview_url"] == "http://preview"


def test_late_cover_reply_does_not_overwrite_newer_cover(window):
    """Regression: rapid voting let an old song's cover land on the new song."""
    label = QLabel()
    label.setProperty("coverUrl", "http://new")

    class Reply:
        def deleteLater(self):
            pass

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def readAll(self):
            return b"not an image"

    reply = Reply()
    window.covers.active_downloads[reply] = ("http://old", label)
    label.setText("Loading...")
    window.covers.on_reply_finished(reply)
    assert label.text() == "Loading..."


def test_audio_preview_uses_cached_url(window):
    add_songs(window)
    key = window.current_pair[1]
    window.session.songs[key]["preview_url"] = "http://cached"
    played = []
    window.audio.play_url = lambda *a: played.append(a)
    window.play_audio_preview("B")
    assert played == [("http://cached", "B")]


def test_recent_files_are_remembered(window, tmp_path):
    add_songs(window)
    path = str(tmp_path / "s.json")
    assert window.save_to(path)
    assert window.settings.recent_files()[0].endswith("s.json")
    assert window.settings.last_dir() == str(tmp_path)
