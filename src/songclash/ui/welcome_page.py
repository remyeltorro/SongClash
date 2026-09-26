"""The page shown while the session is empty."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from songclash import APP_NAME
from songclash.resources import APP_ICON
from songclash.ui.styling import big_button, spaced, styled


class WelcomePage(QWidget):
    add_artist_requested = pyqtSignal()
    open_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        styled(self, "page")
        layout = QVBoxLayout(self)
        layout.addStretch(3)

        icon = QLabel()
        icon.setPixmap(QPixmap(str(APP_ICON)).scaledToHeight(190, Qt.TransformationMode.SmoothTransformation))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        layout.addSpacing(10)

        center = Qt.AlignmentFlag.AlignCenter
        layout.addWidget(spaced(styled(QLabel("TONIGHT'S MAIN EVENT"), "heroTagline"), 4), 0, center)
        layout.addWidget(styled(QLabel(APP_NAME), "heroTitle"), 0, center)
        layout.addWidget(
            styled(QLabel("Two songs enter. One climbs the leaderboard."), "heroSubtitle"), 0, center
        )
        layout.addSpacing(30)

        row = QHBoxLayout()
        row.setSpacing(16)
        row.addStretch()
        row.addWidget(big_button("＋  Add an Artist", "primary", self.add_artist_requested))
        row.addWidget(big_button("Open Session", "ghost", self.open_requested))
        row.addStretch()
        layout.addLayout(row)
        layout.addSpacing(14)
        layout.addWidget(
            styled(QLabel("Ctrl+F  add artist   ·   Ctrl+O  open session"), "keyHint"), 0, center
        )
        layout.addStretch(4)
