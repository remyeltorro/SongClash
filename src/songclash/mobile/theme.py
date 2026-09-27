"""Colors and Pack styles for the touch UI (the desktop "Title Fight" look)."""

import textwrap

import toga
from toga.style import Pack
from toga.style.pack import BOLD, CENTER, COLUMN, ROW

from songclash.mobile.device import tune_button

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

# Usable width of a phone screen in dp (a Moto G7 is 393dp wide), minus margins
SCREEN_WIDTH = 369

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


class Button(toga.Button):
    """A button with native quirks smoothed out (see ``device.tune_button``)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tune_button(self)


def wrap(text: str, width: float = SCREEN_WIDTH, size: float = 14) -> str:
    """Break ``text`` into lines that fit ``width`` dp at font ``size``.

    Toga labels and buttons don't wrap on Android: they ask for the width of
    the whole text and overflow the screen.
    """
    chars = max(8, int(width / (0.62 * size)))
    return "\n".join(textwrap.fill(line, chars) for line in str(text).split("\n"))
