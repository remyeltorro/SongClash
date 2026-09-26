"""Small helpers to tag widgets for the stylesheet in theme.py."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QPushButton, QWidget


def styled(widget, name=None, **props):
    """Tag a widget for theme.py: an objectName plus dynamic properties."""
    if name:
        widget.setObjectName(name)
    for key, value in props.items():
        widget.setProperty(key, value)
    return widget


def spaced(label, pixels):
    """Letter-spacing (not supported by Qt stylesheets)."""
    font = label.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, pixels)
    label.setFont(font)
    return label


def repolish(widget: QWidget):
    """Re-apply the stylesheet after a dynamic property changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def big_button(text, variant, slot, min_width=220):
    """The large pill buttons used on the welcome and battle pages."""
    btn = styled(QPushButton(text), variant=variant, size="big")
    btn.setFixedHeight(46)
    btn.setMinimumWidth(min_width)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(slot)
    return btn


def button(text, variant, slot):
    btn = styled(QPushButton(text), variant=variant)
    btn.clicked.connect(slot)
    return btn
