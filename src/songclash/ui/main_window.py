"""The main window: menus, file handling, and the voting loop.

It owns the RankingSession and wires the pages, windows and helpers
together. Widgets never change the session themselves (except the
leaderboard's editing tools, which report back via ``songs_changed``).
"""

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QStackedWidget

from songclash import APP_NAME
from songclash.core.session import ALL_ALBUMS, RankingSession
from songclash.ui.audio import AudioPreview
from songclash.ui.battle_page import BattlePage
from songclash.ui.covers import CoverLoader
from songclash.ui.importer import ArtistImporter
from songclash.ui.leaderboard import AlbumLeaderboardWindow, LeaderboardWindow
from songclash.ui.settings import AppSettings
from songclash.ui.styling import styled
from songclash.ui.tasks import TaskRunner
from songclash.ui.welcome_page import WelcomePage

SESSION_FILTER = "JSON (*.json)"


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings | None = None):
        super().__init__()
        self.session = RankingSession()
        self.settings = settings or AppSettings()
        self.runner = TaskRunner()
        self.covers = CoverLoader(self)
        self.current_pair = None
        self.leaderboard_win = None
        self.album_win = None

        self.resize(1100, 680)
        self._build_pages()
        self._build_menu()
        self._build_shortcuts()

        self.audio = AudioPreview(self.battle_page.panels, self.runner, self)
        self.audio.message.connect(self.show_message)
        self.importer = ArtistImporter(self, self.runner, self.settings)
        self.importer.imported.connect(self.on_artist_fetched)

        self.refresh_all()
        QTimer.singleShot(0, self.center)

    # ==========================
    # SETUP
    # ==========================
    def _build_pages(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome_page = WelcomePage()
        self.welcome_page.add_artist_requested.connect(self.action_add_artist)
        self.welcome_page.open_requested.connect(self.action_open)

        self.battle_page = BattlePage()
        page = self.battle_page
        page.vote_requested.connect(self.vote)
        page.preview_requested.connect(self.play_audio_preview)
        page.skip_requested.connect(self.skip_matchup)
        page.filter_changed.connect(self.on_filter_changed)
        page.delete_album_requested.connect(self.delete_current_album)
        page.leaderboard_requested.connect(self.show_leaderboard)
        page.album_rankings_requested.connect(self.show_album_leaderboard)

        self.stack.addWidget(self.welcome_page)
        self.stack.addWidget(self.battle_page)

        self.lbl_session = styled(QLabel(), "sessionInfo")
        self.statusBar().addPermanentWidget(self.lbl_session)

    def _build_menu(self):
        menu = self.menuBar()

        def add(menu_, text, slot, shortcut=None):
            act = QAction(text, self)
            if shortcut:
                act.setShortcut(shortcut)
            act.triggered.connect(slot)
            menu_.addAction(act)
            return act

        file_menu = menu.addMenu("&File")
        add(file_menu, "New Session", self.action_new, "Ctrl+N")
        add(file_menu, "Open Session...", self.action_open, "Ctrl+O")
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self.populate_recent_menu)
        add(file_menu, "Save", self.action_save, "Ctrl+S")
        add(file_menu, "Save As...", self.action_save_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        add(file_menu, "Import/Merge JSON...", self.action_merge_file)
        file_menu.addSeparator()
        add(file_menu, "Quit", self.close, "Ctrl+Q")

        edit_menu = menu.addMenu("&Edit")
        self.act_undo = add(edit_menu, "Undo Last Vote", self.undo_vote, "Ctrl+Z")

        art_menu = menu.addMenu("&Add Music")
        add(art_menu, "Add Artist from Web...", self.action_add_artist, "Ctrl+F")

    def _build_shortcuts(self):
        for key, slot in (
            (Qt.Key.Key_Left, lambda: self.vote("A")),
            (Qt.Key.Key_Right, lambda: self.vote("B")),
            (Qt.Key.Key_Down, self.skip_matchup),
        ):
            QShortcut(QKeySequence(key), self, activated=slot)

    def center(self):
        qr = self.frameGeometry()
        qr.moveCenter(self.screen().availableGeometry().center())
        self.move(qr.topLeft())

    def closeEvent(self, event):
        if not self.maybe_save():
            event.ignore()
            return
        self.runner.cancel_all()
        self.audio.stop()
        for win in (self.leaderboard_win, self.album_win):
            if win:
                win.close()
        event.accept()

    # ==========================
    # STATE REFRESH
    # ==========================
    def show_message(self, msg, timeout=5000):
        self.statusBar().showMessage(msg, timeout)

    def refresh_status(self):
        s = self.session
        name = os.path.basename(s.current_filename) if s.current_filename else "Untitled"
        self.setWindowTitle(f"{name}[*] - {APP_NAME}")
        self.setWindowModified(s.has_unsaved_changes)
        self.lbl_session.setText(f"{len(s.songs)} songs  |  {s.votes_this_session} votes this session")
        self.act_undo.setEnabled(bool(s.undo_stack))

    def refresh_windows(self):
        for win in (self.leaderboard_win, self.album_win):
            if win and win.isVisible():
                win.refresh()

    def refresh_filter_list(self):
        # Also resets the session filter if the selected album no longer exists
        self.session.active_filter = self.battle_page.set_albums(
            self.session.get_albums_list(), self.session.active_filter
        )

    def refresh_all(self, new_matchup=True):
        self.refresh_filter_list()
        self.stack.setCurrentWidget(self.battle_page if self.session.songs else self.welcome_page)
        if new_matchup:
            self.next_matchup()
        self.refresh_status()
        self.refresh_windows()

    def on_songs_changed(self, msg):
        """Called after songs were added, removed or merged."""
        pair_gone = not self.current_pair or any(k not in self.session.songs for k in self.current_pair)
        self.refresh_all(new_matchup=pair_gone)
        self.show_message(msg)

    def on_filter_changed(self, text):
        self.session.active_filter = text
        self.next_matchup()
        self.refresh_windows()

    # ==========================
    # FILE ACTIONS
    # ==========================
    def maybe_save(self):
        """Ask to save unsaved changes. Returns False if the user cancelled."""
        if not self.session.has_unsaved_changes or not self.session.songs:
            return True
        buttons = QMessageBox.StandardButton
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Your rankings have unsaved changes. Save them first?",
            buttons.Save | buttons.Discard | buttons.Cancel,
            buttons.Save,
        )
        if reply == buttons.Save:
            return self.action_save()
        return reply == buttons.Discard

    def action_new(self):
        if not self.maybe_save():
            return
        self.session.new_session()
        self.refresh_all()
        self.show_message("New session.")

    def action_open(self):
        if not self.maybe_save():
            return
        fname, _ = QFileDialog.getOpenFileName(self, "Open Session", self.settings.last_dir(), SESSION_FILTER)
        if fname:
            self.open_file(fname)

    def open_file(self, fname):
        try:
            count = self.session.load_from_file(fname)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Open Failed", f"Could not open {fname}:\n\n{e}")
            self.settings.remove_recent(fname)
            return
        self.settings.add_recent(fname)
        self.audio.forget_misses()
        self.refresh_all()
        self.show_message(f"Loaded {count} songs.")

    def action_save(self):
        if not self.session.current_filename:
            return self.action_save_as()
        return self.save_to(self.session.current_filename)

    def action_save_as(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Session", self.settings.last_dir(), SESSION_FILTER)
        return self.save_to(fname) if fname else False

    def save_to(self, fname):
        try:
            self.session.save_session(fname)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save {fname}:\n\n{e}")
            return False
        self.settings.add_recent(fname)
        self.refresh_status()
        self.show_message("Saved.")
        return True

    def action_merge_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Merge Session", self.settings.last_dir(), SESSION_FILTER
        )
        if not fname:
            return
        try:
            count = self.session.merge_file(fname)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Merge Failed", f"Could not read {fname}:\n\n{e}")
            return
        self.on_songs_changed(f"Merged {count} new songs.")

    def populate_recent_menu(self):
        self.recent_menu.clear()
        files = self.settings.recent_files()
        if not files:
            self.recent_menu.addAction("(none)").setEnabled(False)
            return
        for f in files:
            act = self.recent_menu.addAction(f)
            act.triggered.connect(lambda _=False, f=f: self.maybe_save() and self.open_file(f))

    # ==========================
    # ARTIST IMPORT
    # ==========================
    def action_add_artist(self):
        self.importer.start()

    def on_artist_fetched(self, name, songs):
        if not songs:
            QMessageBox.information(
                self,
                "Add Artist",
                f"No songs found for {name} with the selected release types.",
            )
            return
        added = self.session.add_fetched_songs(songs)
        msg = (
            f"Added {added} songs by {name}."
            if added
            else f"All songs by {name} were already in the session."
        )
        self.on_songs_changed(msg)

    # ==========================
    # BATTLE
    # ==========================
    def next_matchup(self):
        self.show_pair(self.session.get_matchup())

    def show_pair(self, pair):
        self.audio.stop()
        self.current_pair = pair
        if not pair:
            self.battle_page.show_pair(None, self.covers)
            if self.session.songs:
                self.show_message("This filter has fewer than 2 songs. Pick another album.", 0)
            return
        self.battle_page.show_pair([self.session.songs[k] for k in pair], self.covers)

    def key_on_side(self, side):
        return self.current_pair[0 if side == "A" else 1] if self.current_pair else None

    def vote(self, side):
        if not self.current_pair or self.stack.currentWidget() is not self.battle_page:
            return
        a, b = self.current_pair
        winner, loser = (a, b) if side == "A" else (b, a)
        self.session.update_score(winner, loser)
        self.next_matchup()
        self.refresh_status()
        self.refresh_windows()

    def undo_vote(self):
        pair = self.session.undo_last_vote()
        if not pair:
            return
        self.show_pair(list(pair))
        self.refresh_status()
        self.refresh_windows()
        self.show_message("Last vote undone.")

    def skip_matchup(self):
        if self.current_pair and self.stack.currentWidget() is self.battle_page:
            self.next_matchup()

    def play_audio_preview(self, side):
        key = self.key_on_side(side)
        if key is not None:
            self.audio.toggle(side, key, self.session.songs.get(key))

    def delete_current_album(self):
        album = self.battle_page.selected_album()
        if album == ALL_ALBUMS:
            QMessageBox.warning(
                self, "Action Denied", "Cannot delete 'All Albums'. Please select a specific album to delete."
            )
            return
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete ALL songs from the album:\n'{album}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = self.session.delete_album(album)
            self.on_songs_changed(f"Deleted album '{album}' ({count} songs removed).")

    # ==========================
    # LEADERBOARDS
    # ==========================
    def show_leaderboard(self):
        if self.leaderboard_win is None:
            self.leaderboard_win = LeaderboardWindow(self.session)
            self.leaderboard_win.songs_changed.connect(self.on_songs_changed)
        self._present(self.leaderboard_win)

    def show_album_leaderboard(self):
        if self.album_win is None:
            self.album_win = AlbumLeaderboardWindow(self.session, self.covers)
        self._present(self.album_win)

    @staticmethod
    def _present(win):
        win.refresh()
        win.show()
        win.raise_()
        win.activateWindow()
