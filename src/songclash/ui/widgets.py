"""Custom-painted and clickable widgets used on the battle page."""

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from songclash.ui.styling import repolish
from songclash.ui.theme import C


class SongCard(QFrame):
    """A large clickable card showing a song title (styled in theme.py)."""

    clicked = pyqtSignal()

    def __init__(self, text="", side="A", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setProperty("side", side)
        self.setProperty("pressed", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)

    def _set_pressed(self, pressed):
        self.setProperty("pressed", pressed)
        repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_pressed(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_pressed(False)
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)


class ClickableLabel(QLabel):
    """A label that emits ``clicked`` on a left click (used for covers)."""

    clicked = pyqtSignal()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class VsEmblem(QWidget):
    """The divider between the two corners: a fading rope with a VS diamond."""

    DIAMOND = 46  # half-diagonal in px

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 160)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        d = self.DIAMOND
        teal, orange = QColor(C["teal"]), QColor(C["orange"])

        # Rope: teal fading in from the top, orange fading out to the bottom
        for y0, y1, color, fade_in in (
            (0, cy - d - 10, teal, True),
            (cy + d + 10, self.height(), orange, False),
        ):
            clear = QColor(color)
            clear.setAlpha(0)
            grad = QLinearGradient(0, y0, 0, y1)
            grad.setColorAt(0, clear if fade_in else color)
            grad.setColorAt(1, color if fade_in else clear)
            p.setPen(QPen(QBrush(grad), 2))
            p.drawLine(QPointF(cx, y0), QPointF(cx, y1))

        diamond = QPolygonF(
            [QPointF(cx, cy - d), QPointF(cx + d, cy), QPointF(cx, cy + d), QPointF(cx - d, cy)]
        )
        # Soft gold glow behind the diamond
        p.setBrush(Qt.BrushStyle.NoBrush)
        for width, alpha in ((18, 14), (11, 26), (6, 40)):
            glow = QColor(C["gold"])
            glow.setAlpha(alpha)
            p.setPen(QPen(glow, width))
            p.drawPolygon(diamond)

        border = QLinearGradient(cx - d, cy - d, cx + d, cy + d)
        border.setColorAt(0, teal)
        border.setColorAt(1, orange)
        fill = QLinearGradient(0, cy - d, 0, cy + d)
        fill.setColorAt(0, QColor(C["surface_hi"]))
        fill.setColorAt(1, QColor(C["bg_deep"]))
        p.setPen(QPen(QBrush(border), 3))
        p.setBrush(QBrush(fill))
        p.drawPolygon(diamond)

        font = QFont(self.font())
        font.setPixelSize(26)
        font.setWeight(QFont.Weight.Black)
        font.setItalic(True)
        p.setFont(font)
        p.setPen(QColor(C["text"]))
        p.drawText(QRectF(cx - d, cy - d, 2 * d, 2 * d), Qt.AlignmentFlag.AlignCenter, "VS")
        p.end()
