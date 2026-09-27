"""Colors and Pack styles for the touch UI (the desktop "Title Fight" look)."""

from toga.style import Pack
from toga.style.pack import BOLD, CENTER, COLUMN, ROW

BG = "#0e1320"
SURFACE = "#161d2e"
SURFACE_HI = "#1e2740"
TEXT = "#e8ecf4"
MUTED = "#8a95ad"
TEAL = "#3fb4c6"
TEAL_DIM = "#1d4f5c"
ORANGE = "#f28c38"
ORANGE_DIM = "#5e3417"
GOLD = "#f5c451"
RED = "#e5534b"

SIDE_COLORS = {"A": (TEAL, TEAL_DIM), "B": (ORANGE, ORANGE_DIM)}
MEDALS = ["🥇", "🥈", "🥉"]


def page(**kw):
    """A full-screen column."""
    return Pack(direction=COLUMN, flex=1, background_color=BG, margin=12, gap=10, **kw)


def column(**kw):
    return Pack(direction=COLUMN, **kw)


def row(**kw):
    return Pack(direction=ROW, align_items=CENTER, **kw)


def heading(size=20, color=GOLD, **kw):
    return Pack(font_size=size, font_weight=BOLD, color=color, **kw)


def text(size=14, color=TEXT, **kw):
    return Pack(font_size=size, color=color, **kw)


def button(color=SURFACE_HI, text_color=TEXT, **kw):
    kw.setdefault("height", 48)
    kw.setdefault("font_size", 15)
    return Pack(background_color=color, color=text_color, **kw)
