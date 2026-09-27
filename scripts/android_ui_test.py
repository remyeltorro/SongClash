"""Drive the installed Android app through its main flows with adb.

Finds widgets by their text (via ``uiautomator dump``), taps them, and saves a
screenshot after each step. Works on an emulator (CI) or a phone connected
with USB debugging:

    adb install -r dist/SongClash.apk
    python scripts/android_ui_test.py --out screenshots

Needs network access on the device (it imports an artist from MusicBrainz
into the current session). ``--fresh`` wipes the app's data first: use it on
emulators only, never on a phone with sessions you care about.
Exits non-zero if a step fails; the screenshots and logcat show where.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "io.github.remyeltorro.songclash"
ARTIST = "Portishead"  # few albums, so the import is quick


@dataclass
class Node:
    text: str
    cls: str
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self):
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2


class Device:
    def __init__(self, out: Path):
        self.out = out
        self.shots = 0
        out.mkdir(parents=True, exist_ok=True)

    def adb(self, *args, binary=False) -> str | bytes:
        result = subprocess.run(["adb", *args], capture_output=True, check=True, timeout=120)
        return result.stdout if binary else result.stdout.decode("utf-8", "replace")

    def shell(self, *args):
        return self.adb("shell", *args)

    def screenshot(self, name):
        self.shots += 1
        path = self.out / f"{self.shots:02d}_{name}.png"
        path.write_bytes(self.adb("exec-out", "screencap", "-p", binary=True))
        print(f"  screenshot {path.name}")

    def nodes(self) -> list[Node]:
        for _ in range(3):  # dump fails while the UI is animating
            try:
                self.shell("uiautomator", "dump", "/sdcard/ui.xml")
                root = ET.fromstring(self.adb("exec-out", "cat", "/sdcard/ui.xml"))
                break
            except (subprocess.CalledProcessError, ET.ParseError):
                time.sleep(1)
        else:
            return []
        found = []
        for n in root.iter("node"):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
            if m:
                found.append(Node(n.get("text", ""), n.get("class", ""), *map(int, m.groups())))
        return found

    def find(self, text, timeout=15, exact=False) -> Node:
        """First node whose text contains ``text`` (case-insensitive)."""
        deadline = time.monotonic() + timeout
        want = text.casefold()
        while True:
            for n in self.nodes():
                have = n.text.casefold()
                if (have == want) if exact else (want in have):
                    return n
            if time.monotonic() > deadline:
                raise AssertionError(f"'{text}' not on screen after {timeout}s")
            time.sleep(1)

    def texts(self) -> list[str]:
        return [n.text for n in self.nodes() if n.text]

    def tap(self, node_or_text, **kw):
        node = self.find(node_or_text, **kw) if isinstance(node_or_text, str) else node_or_text
        x, y = node.center
        self.shell("input", "tap", str(x), str(y))
        time.sleep(1)
        return node

    def long_press(self, node):
        x, y = node.center
        self.shell("input", "swipe", str(x), str(y), str(x), str(y), "1000")
        time.sleep(1)

    def type(self, text):
        self.shell("input", "text", text.replace(" ", "%s"))

    def key(self, name):
        self.shell("input", "keyevent", name)
        time.sleep(1)

    def launch(self):
        self.shell("monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")

    def stop(self):
        self.shell("am", "force-stop", PACKAGE)


def votes(dev) -> int:
    for t in dev.texts():
        m = re.search(r"(\d+) votes this session", t)
        if m:
            return int(m.group(1))
    raise AssertionError("vote counter not found")


def song_button(dev, corner) -> Node:
    """The title button (the vote target) under a corner's label."""
    nodes = dev.nodes()
    label = next(n for n in nodes if n.text.upper() == corner)
    buttons = [n for n in nodes if n.cls.endswith("Button") and n.y1 >= label.y2]
    return min(buttons, key=lambda n: n.y1)


def scenario(dev: Device, fresh: bool):
    dev.stop()
    if fresh:
        step("Fresh start shows the welcome page")
        dev.shell("pm", "clear", PACKAGE)
        dev.launch()
        dev.find("Add an Artist", timeout=90)
        dev.screenshot("welcome")
        dev.tap("Add an Artist")
    else:
        dev.launch()
        dev.tap("＋Artist", timeout=90)

    step(f"Search for {ARTIST}")
    edit = next(n for n in dev.nodes() if n.cls.endswith("EditText"))
    dev.tap(edit)
    dev.type(ARTIST)
    dev.screenshot("search")
    dev.tap("Search", exact=True)
    dev.find("Import Songs", timeout=60)
    dev.screenshot("import_options")

    step("Import the discography")
    dev.tap("Import Songs")
    dev.find("TEAL CORNER", timeout=240)
    time.sleep(8)  # let the covers download
    dev.screenshot("battle")
    start = votes(dev)

    step("Vote five times, then undo once")
    for i in range(5):
        dev.tap(song_button(dev, "TEAL CORNER" if i % 2 else "ORANGE CORNER"))
    assert votes(dev) == start + 5, votes(dev)
    dev.screenshot("after_votes")
    dev.tap("Undo")
    assert votes(dev) == start + 4, votes(dev)

    step("Play an audio preview")
    dev.tap("Preview")
    dev.find("Stop", timeout=30)
    time.sleep(3)
    dev.screenshot("preview_playing")
    dev.tap("Stop")

    step("Filter by album")
    selector = next(n for n in dev.nodes() if n.cls.endswith("Spinner"))
    dev.tap(selector)
    time.sleep(1)
    dev.screenshot("album_picker")
    dev.tap("Dummy")
    dev.screenshot("filtered_battle")

    step("Leaderboards")
    dev.tap("Songs", exact=True)
    dev.find("Leaderboard")
    dev.screenshot("songs")
    dev.long_press(dev.find("1."))
    dev.find("Merge with")
    dev.screenshot("song_actions")
    dev.key("KEYCODE_BACK")
    dev.tap("Albums", exact=True)
    dev.find("Album Rankings")
    time.sleep(4)
    dev.screenshot("albums")

    step("Sessions")
    dev.tap("Sessions", exact=True)
    dev.find("Saved Sessions")
    dev.screenshot("sessions")

    step("The session survives a restart")
    dev.stop()
    dev.launch()
    dev.find("TEAL CORNER", timeout=90)
    assert votes(dev) == 0  # a new app run starts a new vote count...
    dev.tap("Songs", exact=True)
    assert any(re.search(r"· [1-9]\d* votes ·", t) for t in dev.texts())  # ...but keeps the scores
    dev.screenshot("restored")


def step(text):
    print(f"- {text}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=Path("screenshots"))
    parser.add_argument("--fresh", action="store_true", help="clear the app's data first (emulators only)")
    args = parser.parse_args()
    dev = Device(args.out)
    failed = False
    try:
        scenario(dev, args.fresh)
    except Exception as e:
        failed = True
        print(f"FAILED: {type(e).__name__}: {e}")
        try:
            dev.screenshot("failure")
            (args.out / "failure_screen.txt").write_text("\n".join(dev.texts()), encoding="utf-8")
        except Exception:
            pass
    finally:
        (args.out / "logcat.txt").write_bytes(dev.adb("logcat", "-d", binary=True))
    print("FAILED" if failed else "All steps passed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
