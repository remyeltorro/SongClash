"""Generate build/app.ico (the Windows exe icon) from the app's PNG icon."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "songclash" / "assets" / "app_icon.png"
TARGET = ROOT / "build" / "app.ico"


def convert(source=SOURCE, target=TARGET):
    img = Image.open(source).convert("RGBA")
    # Pad to a square so the icon isn't stretched
    side = max(img.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    target.parent.mkdir(parents=True, exist_ok=True)
    square.save(
        target,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Created {target.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        convert()
    except Exception as e:
        sys.exit(f"Error converting icon: {e}")
