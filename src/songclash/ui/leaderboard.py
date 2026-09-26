"""Song and album leaderboard windows."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from songclash.core.export import write_ranking_csv
from songclash.core.session import ALL_ALBUMS
from songclash.ui.dialogs import AddSongDialog
from songclash.ui.styling import button
from songclash.ui.theme import MEDALS

KEY_ROLE = Qt.ItemDataRole.UserRole
MEDAL_ICONS = ["🥇", "🥈", "🥉"]


def _item(text, key=None, numeric=False):
    item = QTableWidgetItem(str(text))
    if key is not None:
        item.setData(KEY_ROLE, key)
    if numeric:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


def _setup_table(table):
    table.setObjectName("rankTable")
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)


def _decorate_rank(item, row):
    """Medal colors (and a medal on the rank number) for the podium."""
    if row < len(MEDALS):
        if item.text() == str(row + 1):
            item.setText(f"{MEDAL_ICONS[row]} {row + 1}")
        item.setForeground(QBrush(QColor(MEDALS[row])))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item


class LeaderboardWindow(QWidget):
    """Song rankings for the current filter, with editing tools.

    Edits go straight to the session; ``songs_changed(message)`` then tells
    the main window to refresh everything.
    """

    COLUMNS = ["Rank", "Song", "Artist", "Album", "Score", "Matches"]

    songs_changed = pyqtSignal(str)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setObjectName("leaderboard")
        self.resize(900, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _setup_table(self.table)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setDefaultSectionSize(34)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.addWidget(button("＋ Add Song", "primary", self.add_manual_song))
        buttons.addWidget(button("Merge Selected", "ghost", self.merge_selected))
        buttons.addWidget(button("Delete Selected", "danger", self.delete_selected))
        buttons.addStretch()
        buttons.addWidget(button("Export Playlist (CSV)", "gold", self.export_csv))
        buttons.addWidget(button("Close", "ghost", self.close))
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        self.setWindowTitle(f"Leaderboard: {self.session.active_filter}")
        selected = set(self.selected_keys())
        keys = self.session.ranked_keys()
        self.table.setRowCount(len(keys))
        for row, key in enumerate(keys):
            s = self.session.songs[key]
            cells = [
                _decorate_rank(_item(row + 1, numeric=True), row),
                _decorate_rank(_item(s["title"], key), row),
                _item(s["artist"]),
                _item(s["album"]),
                _item(int(round(s["score"])), numeric=True),
                _item(s["matches"], numeric=True),
            ]
            for col, cell in enumerate(cells):
                self.table.setItem(row, col, cell)
            if key in selected:
                self.table.selectRow(row)

    def selected_keys(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 1).data(KEY_ROLE) for r in rows if self.table.item(r, 1)]

    def export_csv(self):
        keys = self.session.ranked_keys()
        if not keys:
            QMessageBox.warning(self, "Export", "No songs to export!")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not fname:
            return
        try:
            write_ranking_csv(fname, (self.session.songs[k] for k in keys))
        except OSError as e:
            QMessageBox.critical(self, "Export Failed", str(e))
            return
        QMessageBox.information(
            self,
            "Export Successful",
            f"Exported {len(keys)} songs to:\n{fname}\n\n"
            "You can import this CSV into Spotify using tools like Soundiiz or TuneMyMusic.",
        )

    def delete_selected(self):
        keys = self.selected_keys()
        if not keys:
            return
        reply = QMessageBox.question(
            self,
            "Delete Songs",
            f"Delete {len(keys)} song(s) from the session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        count = self.session.delete_songs(keys)
        self.songs_changed.emit(f"Deleted {count} songs.")

    def add_manual_song(self):
        keys = self.session.get_filtered_keys()
        artist = self.session.songs[keys[0]]["artist"] if keys else ""
        album = self.session.active_filter if self.session.active_filter != ALL_ALBUMS else ""
        dlg = AddSongDialog(self, artist, self.session.get_albums_list(), album)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if self.session.add_song(**data) is None:
            QMessageBox.warning(self, "Error", "That song already exists!")
            return
        self.songs_changed.emit(f"Added manual song: {data['title']}")

    def merge_selected(self):
        keys = self.selected_keys()
        if len(keys) < 2:
            QMessageBox.warning(self, "Merge", "Select at least 2 songs to merge.")
            return
        first_title = self.session.songs[keys[0]]["title"]
        new_title, ok = QInputDialog.getText(
            self, "Merge Songs", "New Title for Merged Song:", text=first_title
        )
        new_title = new_title.strip()
        if not ok or not new_title:
            return
        if self.session.merge_into(keys, new_title) is None:
            QMessageBox.warning(self, "Error", "Target song title already exists!")
            return
        self.songs_changed.emit(f"Merged {len(keys)} songs into '{new_title}'.")


class AlbumLeaderboardWindow(QWidget):
    """Albums ranked by the average score of their songs."""

    def __init__(self, session, covers):
        super().__init__()
        self.session = session
        self.covers = covers
        self.setObjectName("leaderboard")
        self.setWindowTitle("Album Rankings")
        self.resize(800, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Rank", "Cover", "Album", "Avg Score", "Songs"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 80)
        _setup_table(self.table)
        self.table.verticalHeader().setDefaultSectionSize(76)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Close", "ghost", self.close))
        layout.addLayout(row)

        self.refresh()

    def refresh(self):
        albums = self.session.album_stats()
        self.table.setRowCount(len(albums))
        for row, a in enumerate(albums):
            self.table.setItem(row, 0, _decorate_rank(_item(row + 1, numeric=True), row))

            cover = QLabel()
            cover.setObjectName("cover")
            cover.setFixedSize(64, 64)
            cover.setScaledContents(True)
            cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(6, 6, 6, 6)
            holder_layout.addWidget(cover)
            self.table.setCellWidget(row, 1, holder)
            self.covers.load(a["cover_url"], cover)

            self.table.setItem(row, 2, _decorate_rank(_item(f"{a['album']}\n{a['artist']}"), row))
            self.table.setItem(row, 3, _item(f"{a['avg']:.1f}", numeric=True))
            self.table.setItem(row, 4, _item(a["count"], numeric=True))
