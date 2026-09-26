"""Paths to files bundled with the package.

Assets live in ``songclash/assets``. PyInstaller keeps that layout inside the
exe (see packaging/songclash.spec) and sets ``__file__`` accordingly, so the
same lookup works from source, from an installed wheel and from the exe.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

APP_ICON = ASSETS_DIR / "app_icon.png"


def asset(name: str) -> str:
    """Absolute path of a bundled asset, as a string for Qt APIs."""
    return str(ASSETS_DIR / name)
