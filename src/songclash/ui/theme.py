"""SongClash theme: "Title Fight".

A boxing-night look built from the app icon's colors: a teal corner vs an
orange corner on a deep midnight stage, with gold for the crown/VS.
Widgets opt in to special styles via objectName or dynamic properties such as
"variant", "side" and "size" (see ``styling.styled``).
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

C = {
    "bg": "#0e1320",  # stage
    "bg_deep": "#0a0e18",
    "surface": "#161d2e",
    "surface_hi": "#1e2740",
    "border": "#2a3552",
    "text": "#e8ecf4",
    "muted": "#8a95ad",
    "faint": "#4a5570",
    "teal": "#3fb4c6",  # corner A (treble clef)
    "teal_dim": "#1d4f5c",
    "orange": "#f28c38",  # corner B (music note)
    "orange_dim": "#5e3417",
    "gold": "#f5c451",  # crown
    "green": "#5fbf8a",  # podium
    "red": "#e5534b",
}

STYLESHEET = """
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
    font-size: 14px;
    color: {text};
}}
QMainWindow, QDialog, QWidget#page {{
    background: qradialgradient(cx:0.5, cy:0.35, radius:0.9, fx:0.5, fy:0.3,
        stop:0 #18223a, stop:0.6 {bg}, stop:1 {bg_deep});
}}
QWidget#leaderboard {{ background: {bg}; }}
QToolTip {{
    background: {surface_hi}; color: {text};
    border: 1px solid {gold}; border-radius: 6px; padding: 5px 8px;
}}

/* ---------- Menu & status bar ---------- */
QMenuBar {{ background: {bg_deep}; border-bottom: 1px solid {border}; padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; padding: 6px 12px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {surface_hi}; color: {gold}; }}
QMenu {{ background: {surface}; border: 1px solid {border}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background: {surface_hi}; color: {gold}; }}
QMenu::item:disabled {{ color: {faint}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}
QStatusBar {{ background: {bg_deep}; border-top: 1px solid {border}; color: {muted}; }}
QStatusBar QLabel {{ color: {muted}; }}
QLabel#sessionInfo {{ color: {gold}; font-weight: 600; padding: 0 10px; }}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {surface_hi}; border: 1px solid {border}; border-radius: 8px;
    padding: 7px 16px; font-weight: 600;
}}
QPushButton:hover {{ border-color: {gold}; }}
QPushButton:pressed {{ background: {surface}; }}
QPushButton:disabled {{ color: {faint}; border-color: {surface_hi}; }}
QPushButton:default {{ border-color: {teal}; }}

QPushButton[variant="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {teal}, stop:1 #2f8fb0);
    border: none; color: #04141a;
}}
QPushButton[variant="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5fd0e0, stop:1 {teal});
}}
QPushButton[variant="accent"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {orange}, stop:1 #e0612b);
    border: none; color: #1e0d02;
}}
QPushButton[variant="accent"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffab62, stop:1 {orange});
}}
QPushButton[variant="gold"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd978, stop:1 #e0a82e);
    border: none; color: #2a1c00;
}}
QPushButton[variant="gold"]:hover {{ background: #ffe08f; }}
QPushButton[variant="danger"] {{ background: transparent; border: 1px solid {red}; color: {red}; }}
QPushButton[variant="danger"]:hover {{ background: {red}; color: white; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid {border}; color: {muted}; }}
QPushButton[variant="ghost"]:hover {{ color: {text}; border-color: {muted}; }}

QPushButton[size="big"] {{ border-radius: 23px; padding: 0 30px; font-size: 16px; font-weight: 700; }}

/* ---------- Battle stage ---------- */
QPushButton#skipButton {{
    background: transparent; border: 1px dashed {faint}; border-radius: 18px;
    color: {muted}; padding: 8px 18px; font-weight: 600;
}}
QPushButton#skipButton:hover {{ border: 1px solid {muted}; color: {text}; }}
QPushButton#skipButton:disabled {{ color: {faint}; border-color: {surface_hi}; }}
QLabel#keyHint {{ color: {faint}; font-size: 12px; }}

QLabel#cover {{
    background: {surface}; border: 1px solid {border}; border-radius: 10px;
    color: {faint}; font-size: 12px;
}}
QLabel#cover[side="A"] {{ border: 2px solid {teal}; padding: 4px; background: {teal_dim}; }}
QLabel#cover[side="B"] {{ border: 2px solid {orange}; padding: 4px; background: {orange_dim}; }}
QLabel#songMeta {{ color: {muted}; font-size: 13px; }}
QLabel#cornerTag[side="A"] {{ color: {teal}; font-size: 11px; font-weight: 800; }}
QLabel#cornerTag[side="B"] {{ color: {orange}; font-size: 11px; font-weight: 800; }}

SongCard {{
    border-radius: 18px; border: 2px solid {border};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {surface_hi}, stop:1 {surface});
}}
SongCard QLabel {{ font-size: 26px; font-weight: 800; color: {text}; background: transparent; border: none; }}
SongCard[side="A"]:hover {{
    border-color: {teal};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1f4a58, stop:1 {surface});
}}
SongCard[side="B"]:hover {{
    border-color: {orange};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #55341c, stop:1 {surface});
}}
SongCard[pressed="true"] {{ border-color: {gold}; background: {bg_deep}; }}
SongCard:disabled {{ background: {surface}; border: 2px dashed {border}; }}
SongCard QLabel:disabled {{ color: {faint}; }}

QPushButton#audioButton {{
    border: 2px solid transparent; border-radius: 18px; padding: 6px 22px; font-size: 14px; font-weight: 800;
}}
QPushButton#audioButton[side="A"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {teal}, stop:1 #2f8fb0); color: #04141a;
}}
QPushButton#audioButton[side="B"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {orange}, stop:1 #e0612b); color: #1e0d02;
}}
QPushButton#audioButton[side="A"]:hover {{ background: #5fd0e0; }}
QPushButton#audioButton[side="B"]:hover {{ background: #ffab62; }}
QPushButton#audioButton[side="A"][playing="true"] {{ background: transparent; border: 2px solid {teal}; color: {teal}; }}
QPushButton#audioButton[side="B"][playing="true"] {{ background: transparent; border: 2px solid {orange}; color: {orange}; }}
QPushButton#audioButton:disabled {{ background: {surface_hi}; color: {faint}; }}
QLabel#cover:hover {{ border-color: {gold}; }}
QProgressBar#audioProgress {{ background: {surface_hi}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar#audioProgress[side="A"]::chunk {{ background: {teal}; border-radius: 2px; }}
QProgressBar#audioProgress[side="B"]::chunk {{ background: {orange}; border-radius: 2px; }}

/* ---------- Welcome ---------- */
QLabel#heroTitle {{ font-size: 54px; font-weight: 900; color: {text}; }}
QLabel#heroSubtitle {{ font-size: 17px; color: {muted}; }}
QLabel#heroTagline {{ font-size: 12px; color: {gold}; font-weight: 800; }}

/* ---------- Inputs ---------- */
QComboBox, QLineEdit {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px;
    padding: 6px 10px; selection-background-color: {teal}; selection-color: #04141a;
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {muted}; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {teal}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px;
    selection-background-color: {surface_hi}; selection-color: {gold}; outline: none; padding: 4px;
}}
QCheckBox {{ spacing: 10px; padding: 3px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid {faint}; background: {surface};
}}
QCheckBox::indicator:hover {{ border-color: {teal}; }}
QCheckBox::indicator:checked {{ background: {teal}; border-color: {teal}; }}
QLabel#dialogHeading {{ font-size: 15px; font-weight: 700; color: {gold}; }}

/* ---------- Tables & lists ---------- */
QTableWidget, QListWidget {{
    background: {surface}; alternate-background-color: #1a2236;
    border: 1px solid {border}; border-radius: 10px; gridline-color: transparent;
    selection-background-color: {surface_hi}; selection-color: {gold}; outline: none;
}}
QTableWidget::item, QListWidget::item {{ padding: 6px; border: none; }}
QListWidget::item:hover {{ background: {surface_hi}; }}
QHeaderView::section {{
    background: {bg_deep}; color: {muted}; border: none; border-bottom: 2px solid {gold};
    padding: 8px 6px; font-size: 12px; font-weight: 700;
}}
QTableCornerButton::section {{ background: {bg_deep}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {faint}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 3px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QProgressDialog QProgressBar {{
    background: {surface}; border: 1px solid {border}; border-radius: 6px;
    text-align: center; min-height: 14px;
}}
QProgressDialog QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {teal}, stop:1 {orange});
    border-radius: 5px;
}}
QMessageBox QLabel {{ font-size: 14px; }}
""".format(**C)

# Medal colors for the top 3 rows of the leaderboards
MEDALS = ["#f5c451", "#c9d3e3", "#d9905a"]


def palette():
    """Base palette so native bits (dialogs, disabled text) match the theme."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: C["bg"],
        QPalette.ColorRole.WindowText: C["text"],
        QPalette.ColorRole.Base: C["surface"],
        QPalette.ColorRole.AlternateBase: "#1a2236",
        QPalette.ColorRole.ToolTipBase: C["surface_hi"],
        QPalette.ColorRole.ToolTipText: C["text"],
        QPalette.ColorRole.Text: C["text"],
        QPalette.ColorRole.Button: C["surface_hi"],
        QPalette.ColorRole.ButtonText: C["text"],
        QPalette.ColorRole.BrightText: C["red"],
        QPalette.ColorRole.Link: C["teal"],
        QPalette.ColorRole.Highlight: C["teal"],
        QPalette.ColorRole.HighlightedText: "#04141a",
        QPalette.ColorRole.PlaceholderText: C["faint"],
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(C["faint"]))
    return p


def apply(app: QApplication):
    """Install the theme on the whole application."""
    app.setStyle("Fusion")
    app.setPalette(palette())
    app.setStyleSheet(STYLESHEET)
