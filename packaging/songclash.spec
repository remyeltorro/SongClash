# PyInstaller build definition. Used by build.bat and the release workflow:
#   python scripts/make_icon.py
#   pyinstaller --noconfirm packaging/songclash.spec
# -*- mode: python ; coding: utf-8 -*-
import os

ROOT = os.path.dirname(SPECPATH)  # noqa: F821 (SPECPATH is injected by PyInstaller)
SRC = os.path.join(ROOT, "src")

a = Analysis(  # noqa: F821
    [os.path.join(SPECPATH, "launcher.py")],  # noqa: F821
    pathex=[SRC],
    datas=[(os.path.join(SRC, "songclash", "assets"), "songclash/assets")],
    excludes=["PyQt5", "tkinter"],
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SongClash",
    console=False,
    upx=True,
    icon=[os.path.join(ROOT, "build", "app.ico")],
)
