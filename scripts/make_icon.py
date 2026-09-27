"""Generate app icons from the app's PNG icon.

python scripts/make_icon.py            build/app.ico (the Windows exe icon)
python scripts/make_icon.py --android  build/icons/songclash-*.png (Briefcase)
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "songclash" / "assets" / "app_icon.png"
TARGET = ROOT / "build" / "app.ico"
ANDROID_DIR = ROOT / "build" / "icons"

# Briefcase looks for {icon}-{variant}-{size}.png
ANDROID_SIZES = {
    "round": [48, 72, 96, 144, 192],
    "square": [48, 72, 96, 144, 192],
    # Adaptive icons are masked to a circle/squircle: the artwork must sit in
    # the inner 66% "safe zone"
    "adaptive": [108, 162, 216, 324, 432],
}
BACKGROUND = (14, 19, 32, 255)  # the theme's midnight "stage"


def square(img, pad=0.0, background=(0, 0, 0, 0)):
    """Pad to a square (plus ``pad`` of the side on each edge) so nothing is stretched."""
    side = max(img.size)
    canvas_side = int(side * (1 + 2 * pad))
    canvas = Image.new("RGBA", (canvas_side, canvas_side), background)
    canvas.paste(img, ((canvas_side - img.width) // 2, (canvas_side - img.height) // 2), img)
    return canvas


def convert(source=SOURCE, target=TARGET):
    img = square(Image.open(source).convert("RGBA"))
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        target,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Created {target.relative_to(ROOT)}")


def android(source=SOURCE, out_dir=ANDROID_DIR):
    img = Image.open(source).convert("RGBA")
    variants = {
        "round": square(img, 0.08, BACKGROUND),
        "square": square(img, 0.08, BACKGROUND),
        "adaptive": square(img, 0.25),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for variant, sizes in ANDROID_SIZES.items():
        for size in sizes:
            variants[variant].resize((size, size), Image.LANCZOS).save(
                out_dir / f"songclash-{variant}-{size}.png"
            )
    print(f"Created Android icons in {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        android() if "--android" in sys.argv else convert()
    except Exception as e:
        sys.exit(f"Error converting icon: {e}")
