"""The "Title Fight" look of the desktop app, rebuilt for Toga.

Colors come from ``songclash.ui.theme``: a teal corner vs an orange corner
on a midnight stage, with gold for the crown and the VS emblem. Pack styles
handle layout, fonts and colors; ``device`` adds what Pack can't (rounded
corners, borders, gradients) on Android.
"""

import textwrap

import toga
from toga.style import Pack
from toga.style.pack import BOLD, CENTER, COLUMN, ROW

from songclash.mobile import device

BG = "#0e1320"  # stage
BG_DEEP = "#0a0e18"
SURFACE = "#161d2e"
SURFACE_HI = "#1e2740"
BORDER = "#2a3552"
TEXT = "#e8ecf4"
MUTED = "#8a95ad"
FAINT = "#4a5570"
TEAL = "#3fb4c6"  # corner A
TEAL_DEEP = "#2f8fb0"
TEAL_DIM = "#1d4f5c"
ORANGE = "#f28c38"  # corner B
ORANGE_DEEP = "#e0612b"
ORANGE_DIM = "#5e3417"
GOLD = "#f5c451"  # crown
GOLD_LIGHT = "#ffd978"
GOLD_DEEP = "#e0a82e"
RED = "#e5534b"
RIPPLE = "#33ffffff"

SIDE_COLORS = {"A": (TEAL, TEAL_DIM), "B": (ORANGE, ORANGE_DIM)}
MEDALS = ["#f5c451", "#c9d3e3", "#d9905a"]  # gold, silver, bronze
MEDAL_ICONS = ["🥇", "🥈", "🥉"]

# Usable width of a phone screen in dp (a Moto G54 is about 411dp wide), minus margins
SCREEN_WIDTH = 350


# ---------- Pack helpers ----------


def page(**kw):
    """A full-screen column."""
    return Pack(direction=COLUMN, flex=1, background_color=BG, margin=(12, 14), gap=12, **kw)


def row(**kw):
    return Pack(direction=ROW, align_items=CENTER, **kw)


def heading(size=20, color=GOLD, **kw):
    return Pack(font_size=size, font_weight=BOLD, color=color, **kw)


def text(size=14, color=TEXT, **kw):
    return Pack(font_size=size, color=color, **kw)


def wrap(text: str, width: float = SCREEN_WIDTH, size: float = 14) -> str:
    """Break ``text`` into lines that fit ``width`` dp at font ``size``.

    Toga labels and buttons don't wrap on Android: they ask for the width of
    the whole text and overflow the screen.
    """
    chars = max(8, int(width / (0.58 * size)))
    return "\n".join(textwrap.fill(line, chars) for line in str(text).split("\n"))


# ---------- Components ----------


class Button(toga.Button):
    """A button with native quirks smoothed out (see ``device.tune_button``).

    Toga keeps only the first line of a button's text; on Android this one
    shows every line (wrapped song titles, icon + label tabs).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        device.tune_button(self)

    @property
    def text(self) -> str:
        return getattr(self, "_full_text", "")

    @text.setter
    def text(self, value):
        toga.Button.text.fset(self, value)
        self._full_text = "" if value is None else str(value)
        if "\n" in self._full_text and device.set_text(self, self._full_text):
            self.refresh()


def skin(widget, fill=None, **shape):
    """Rounded native background, or a flat Pack color where that's unavailable."""
    if not device.shape(widget, fill=fill, **shape):
        color = fill or (shape.get("gradient") or [None])[0]
        if color:
            widget.style.background_color = color
    return widget


# kind -> (shape arguments, text color); the desktop's QPushButton variants
PILLS = {
    "gold": ({"gradient": [GOLD_LIGHT, GOLD_DEEP], "vertical": True}, "#2a1c00"),
    "teal": ({"gradient": [TEAL, TEAL_DEEP]}, "#04141a"),
    "orange": ({"gradient": [ORANGE, ORANGE_DEEP]}, "#1e0d02"),
    "teal_outline": ({"stroke": TEAL, "stroke_width": 2}, TEAL),
    "orange_outline": ({"stroke": ORANGE, "stroke_width": 2}, ORANGE),
    "ghost": ({"stroke": BORDER}, MUTED),
    "danger": ({"stroke": RED}, RED),
    "surface": ({"fill": SURFACE_HI, "stroke": BORDER, "stroke_width": 1}, TEXT),
    "tab": ({}, MUTED),
    "tab_active": ({"fill": SURFACE_HI}, GOLD),
}


def pill(label, on_press=None, kind="surface", height=44, radius=None, size=15, **style):
    """A rounded button in one of the PILLS variants."""
    button = Button(
        label,
        on_press=on_press,
        style=Pack(height=height, font_size=size, font_weight=BOLD, text_align=CENTER, **style),
    )
    button._radius = height / 2 if radius is None else radius
    restyle(button, kind)
    return button


def restyle(button, kind):
    """Switch a pill to another variant (e.g. Play -> Stop)."""
    shape, color = PILLS[kind]
    button.style.color = color
    skin(button, radius=button._radius, ripple=RIPPLE, **shape)


def card(*children, stroke=BORDER, fill=SURFACE, radius=16, padding=12, gap=8, stroke_width=1.5):
    """A rounded, bordered panel stacking ``children``.

    Pack has no padding (margin moves the box itself), so the children sit
    in an inner box whose margin pads them away from the border.
    """
    inner = toga.Box(children=list(children), style=Pack(direction=COLUMN, flex=1, gap=gap, margin=padding))
    outer = toga.Box(children=[inner], style=Pack(direction=COLUMN))
    return skin(outer, fill=fill, stroke=stroke, stroke_width=stroke_width, radius=radius)


def corner_tag(label, color, size=11):
    """The spaced-out "TEAL CORNER" caption."""
    tag = toga.Label(label, style=Pack(font_size=size, font_weight=BOLD, color=color))
    device.letter_spacing(tag, 0.3)
    return tag


def vs_emblem():
    """The "VS" badge between the corners: gold ring with a soft glow."""
    label = toga.Label(
        "VS",
        style=Pack(width=64, height=64, font_size=18, font_weight=BOLD, color=GOLD, text_align=CENTER),
    )
    device.badge(label, fill=SURFACE_HI, stroke=GOLD, glow="#40f5c451")
    return label


def muted(label, size=13, **style):
    return toga.Label(label, style=text(size, MUTED, **style))


def text_input(**kw):
    field = toga.TextInput(style=Pack(flex=1, font_size=16, color=TEXT), **kw)
    device.tint(field, GOLD)
    return field


def switch(label, value=False):
    sw = toga.Switch(label, value=value, style=Pack(font_size=15, color=TEXT, margin=(4, 2)))
    device.tint(sw, TEAL, off=FAINT)
    return sw
