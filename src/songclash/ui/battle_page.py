"""The battle page: two song corners, the VS emblem and the album filter.

The page only displays state and emits signals; MainWindow decides what a
vote, skip or filter change does.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from songclash.core.session import ALL_ALBUMS
from songclash.ui.styling import big_button, repolish, spaced, styled
from songclash.ui.widgets import ClickableLabel, SongCard, VsEmblem

SIDES = ("A", "B")
CORNER_NAMES = {"A": "TEAL CORNER", "B": "ORANGE CORNER"}
KEY_HINTS = {"A": "←", "B": "→"}
PLAY_TEXT = "▶   Play Preview"
STOP_TEXT = "■   Stop Preview"


def song_caption(song):
    """ "Artist · Album (Year)", without repeating a year already in the album."""
    album = song["album"]
    if song["year"] not in album:
        album = f"{album} ({song['year']})"
    return f"{song['artist']} · {album}"


class BattlePanel(QWidget):
    """One corner: cover, title card, caption and audio preview controls."""

    vote_clicked = pyqtSignal()
    preview_clicked = pyqtSignal()

    def __init__(self, side, parent=None):
        super().__init__(parent)
        self.side = side
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        tag = spaced(styled(QLabel(CORNER_NAMES[side]), "cornerTag", side=side), 3)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cover = styled(ClickableLabel(), "cover", side=side)
        self.cover.setFixedSize(212, 212)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setScaledContents(True)
        self.cover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover.setToolTip("Click to play a 30-second preview")
        self.cover.clicked.connect(self.preview_clicked)

        self.card = SongCard(f"Song {side}", side)
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.card.setMinimumHeight(120)
        self.card.setToolTip(f"Click or press {KEY_HINTS[side]} to pick this song")
        self.card.clicked.connect(self.vote_clicked)

        self.caption = styled(QLabel(""), "songMeta")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setWordWrap(True)

        self.audio_button = styled(QPushButton(PLAY_TEXT), "audioButton", side=side, playing=False)
        self.audio_button.setMinimumWidth(200)
        self.audio_button.setFixedHeight(38)
        self.audio_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.audio_button.clicked.connect(self.preview_clicked)

        self.progress = styled(QProgressBar(), "audioProgress", side=side)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        policy = self.progress.sizePolicy()
        policy.setRetainSizeWhenHidden(True)  # no layout jump when playback starts
        self.progress.setSizePolicy(policy)
        self.progress.setVisible(False)

        layout.addWidget(tag)
        layout.addWidget(self.cover, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.card)
        layout.addWidget(self.caption)
        audio_layout = QVBoxLayout()
        audio_layout.setSpacing(4)
        audio_layout.addWidget(self.audio_button, 0, Qt.AlignmentFlag.AlignCenter)
        audio_layout.addWidget(self.progress)
        layout.addLayout(audio_layout)

    def show_song(self, song, covers):
        self.card.setText(song["title"])
        self.caption.setText(song_caption(song))
        covers.load(song.get("cover_url"), self.cover)

    def clear(self):
        self.card.setText("-")
        self.caption.setText("")
        self.cover.clear()

    def set_active(self, enabled):
        self.card.setEnabled(enabled)
        self.audio_button.setEnabled(enabled)

    # Audio preview display, driven by AudioPreview
    def set_audio_idle(self):
        self._set_audio_button(PLAY_TEXT, playing=False)
        self.progress.setVisible(False)
        self.progress.setValue(0)

    def set_audio_playing(self):
        self._set_audio_button(STOP_TEXT, playing=True)
        self.progress.setValue(0)
        self.progress.setVisible(True)

    def set_audio_text(self, text):
        self.audio_button.setText(text)

    def _set_audio_button(self, text, playing):
        self.audio_button.setText(text)
        self.audio_button.setProperty("playing", playing)
        repolish(self.audio_button)


class BattlePage(QWidget):
    vote_requested = pyqtSignal(str)  # side
    preview_requested = pyqtSignal(str)  # side
    skip_requested = pyqtSignal()
    filter_changed = pyqtSignal(str)
    delete_album_requested = pyqtSignal()
    leaderboard_requested = pyqtSignal()
    album_rankings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        styled(self, "page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(18)
        layout.addLayout(self._build_top_bar())
        layout.addLayout(self._build_arena())
        layout.addLayout(self._build_footer())

    def _build_top_bar(self):
        bar = QHBoxLayout()
        self.combo_filter = QComboBox()
        self.combo_filter.addItem(ALL_ALBUMS)
        self.combo_filter.setMinimumWidth(320)
        self.combo_filter.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.combo_filter.currentTextChanged.connect(self.filter_changed)
        bar.addWidget(styled(QLabel("Weight class:"), "songMeta"))
        bar.addWidget(self.combo_filter)

        self.btn_delete_album = styled(QPushButton("Delete Album"), variant="danger")
        self.btn_delete_album.setToolTip("Delete every song of the selected album")
        self.btn_delete_album.clicked.connect(self.delete_album_requested)
        bar.addWidget(self.btn_delete_album)
        bar.addStretch()
        return bar

    def _build_arena(self):
        arena = QHBoxLayout()
        arena.setSpacing(20)
        self.panels = {side: BattlePanel(side) for side in SIDES}
        for side, panel in self.panels.items():
            panel.vote_clicked.connect(lambda side=side: self.vote_requested.emit(side))
            panel.preview_clicked.connect(lambda side=side: self.preview_requested.emit(side))

        middle = QVBoxLayout()
        middle.addWidget(VsEmblem(), 1, Qt.AlignmentFlag.AlignHCenter)
        self.btn_skip = styled(QPushButton("Skip  ↓"), "skipButton")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.clicked.connect(self.skip_requested)
        middle.addWidget(self.btn_skip, 0, Qt.AlignmentFlag.AlignCenter)
        hint = styled(QLabel("← / →  vote\nCtrl+Z  undo"), "keyHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.addWidget(hint)

        arena.addWidget(self.panels["A"], 4)
        arena.addLayout(middle, 1)
        arena.addWidget(self.panels["B"], 4)
        return arena

    def _build_footer(self):
        footer = QHBoxLayout()
        footer.setSpacing(16)
        footer.addStretch(1)
        footer.addWidget(big_button("♛   Leaderboard", "gold", self.leaderboard_requested, 240))
        footer.addWidget(big_button("◉   Album Rankings", "ghost", self.album_rankings_requested, 240))
        footer.addStretch(1)
        return footer

    def set_albums(self, albums, current):
        """Re-populate the album filter without emitting ``filter_changed``.

        Keeps ``current`` selected if it still exists. Returns the selection.
        """
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        self.combo_filter.addItem(ALL_ALBUMS)
        self.combo_filter.addItems(albums)
        self.combo_filter.setCurrentIndex(max(self.combo_filter.findText(current), 0))
        self.combo_filter.blockSignals(False)
        return self.combo_filter.currentText()

    def selected_album(self):
        return self.combo_filter.currentText()

    def show_pair(self, songs, covers):
        """Display two songs, or an empty, disabled arena if ``songs`` is None."""
        self.set_active(songs is not None)
        for i, panel in enumerate(self.panels.values()):
            if songs is None:
                panel.clear()
            else:
                panel.show_song(songs[i], covers)

    def set_active(self, enabled):
        for panel in self.panels.values():
            panel.set_active(enabled)
        self.btn_skip.setEnabled(enabled)
