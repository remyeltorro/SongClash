"""Android services (audio, file picking), with desktop fallbacks.

The Android parts talk to Java through Chaquopy, which Briefcase bundles.
On a desktop (``python -m songclash.mobile``) Toga's file dialogs are used
and audio previews are unavailable.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import sys
from collections.abc import Callable
from pathlib import Path

import toga

IS_ANDROID = hasattr(sys, "getandroidapilevel") or sys.platform == "android"

# on_finished(error): error is None when the preview simply ended
Finished = Callable[[str | None], None]


class NullPlayer:
    """Stand-in on platforms without a media player."""

    def play(self, url: str, on_started: Callable[[], None], on_finished: Finished):
        on_finished("Audio previews only play in the Android app.")

    def stop(self):
        pass

    def progress(self) -> float:
        return 0.0


class AndroidPlayer:
    """Streams one URL at a time with android.media.MediaPlayer."""

    def __init__(self):
        from android.media import AudioAttributes, MediaPlayer
        from java import dynamic_proxy

        self._MediaPlayer = MediaPlayer
        self._attributes = (
            AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
            .build()
        )
        self.player = None
        self.prepared = False
        self.generation = 0

        owner = self

        class Listener(
            dynamic_proxy(
                MediaPlayer.OnPreparedListener,
                MediaPlayer.OnCompletionListener,
                MediaPlayer.OnErrorListener,
            )
        ):
            """Callbacks for one play() call; stale ones are ignored."""

            def __init__(self, generation, on_started, on_finished):
                super().__init__()
                self.generation = generation
                self.on_started = on_started
                self.on_finished = on_finished

            def current(self):
                return self.generation == owner.generation

            def onPrepared(self, mp):
                if self.current():
                    owner.prepared = True
                    mp.start()
                    self.on_started()

            def onCompletion(self, mp):
                if self.current():
                    owner.stop()
                    self.on_finished(None)

            def onError(self, mp, what, extra):
                if self.current():
                    owner.stop()
                    self.on_finished(f"Could not play preview (error {what}/{extra}).")
                return True

        self._Listener = Listener

    def play(self, url, on_started, on_finished):
        self.stop()
        self.generation += 1
        # MediaPlayer calls back from Java, outside the asyncio loop Toga's UI
        # runs in; hop back onto that loop before touching any widget.
        loop = asyncio.get_event_loop()
        listener = self._Listener(
            self.generation,
            lambda: loop.call_soon_threadsafe(on_started),
            lambda error: loop.call_soon_threadsafe(on_finished, error),
        )
        player = self._MediaPlayer()
        player.setAudioAttributes(self._attributes)
        player.setOnPreparedListener(listener)
        player.setOnCompletionListener(listener)
        player.setOnErrorListener(listener)
        self.player, self._listener = player, listener
        try:
            player.setDataSource(url)
            player.prepareAsync()
        except Exception as e:  # Java exceptions surface as Python exceptions
            self.stop()
            on_finished(f"Could not play preview: {e}")

    def stop(self):
        self.generation += 1
        player, self.player, self.prepared = self.player, None, False
        if player is not None:
            with contextlib.suppress(Exception):  # stop() throws if playback never started
                player.stop()
            player.release()

    def progress(self) -> float:
        """Playback position, from 0 to 1."""
        if not self.player or not self.prepared:
            return 0.0
        duration = self.player.getDuration()
        return self.player.getCurrentPosition() / duration if duration > 0 else 0.0


# ---------- Native styling ----------
#
# Toga's Pack styles can't round corners, draw borders or gradients. On
# Android these helpers put GradientDrawables behind widgets instead. Each
# returns False on other platforms so callers can fall back to Pack styles.


_density: float | None = None


def _dp(native, value: float) -> int:
    global _density
    if _density is None:
        _density = native.getResources().getDisplayMetrics().density
    return int(value * _density + 0.5)


@functools.cache
def _color(value: str) -> int:
    from android.graphics import Color

    return Color.parseColor(value)


def tune_button(button: toga.Button):
    """Android buttons default to ALL CAPS, an 88x48dp minimum size and
    extra padding, which shouts song titles and overflows rows of buttons."""
    if not IS_ANDROID:
        return
    native = button._impl.native
    native.setAllCaps(False)
    native.setMinWidth(0)
    native.setMinimumWidth(0)
    native.setMinHeight(0)
    native.setMinimumHeight(0)
    native.setSingleLine(False)
    native.setMaxLines(3)
    pad = _dp(native, 8)
    native.setPadding(pad, 0, pad, 0)


def set_text(widget: toga.Widget, text: str) -> bool:
    """Set a TextView's text directly, bypassing Toga's single-line rule."""
    if not IS_ANDROID:
        return False
    widget._impl.native.setText(text)
    return True


def shape(
    widget: toga.Widget,
    fill: str | None = None,
    radius: float = 12,
    stroke: str | None = None,
    stroke_width: float = 1.5,
    gradient: list[str] | None = None,
    vertical: bool = False,
    ripple: str | None = None,
) -> bool:
    """Give ``widget`` a rounded background, optionally bordered or gradient-filled."""
    if not IS_ANDROID:
        return False
    from android.content.res import ColorStateList
    from android.graphics.drawable import GradientDrawable, RippleDrawable

    native = widget._impl.native
    d = GradientDrawable()
    if gradient:
        orientation = GradientDrawable.Orientation
        d.setOrientation(orientation.TOP_BOTTOM if vertical else orientation.LEFT_RIGHT)
        d.setColors([_color(c) for c in gradient])
    else:
        d.setColor(_color(fill) if fill else 0)
    d.setCornerRadius(_dp(native, radius))
    if stroke:
        d.setStroke(_dp(native, stroke_width), _color(stroke))
    background = RippleDrawable(ColorStateList.valueOf(_color(ripple)), d, None) if ripple else d
    native.setBackground(background)
    # Drop the Material press shadow, which draws outside our shape
    native.setStateListAnimator(None)
    native.setElevation(0)
    native.setClipToOutline(True)  # clips images to the rounded corners
    return True


def badge(widget: toga.Widget, fill: str, stroke: str, glow: str) -> bool:
    """A round badge with a glowing ring behind ``widget``'s text (the VS emblem)."""
    if not IS_ANDROID:
        return False
    from android.graphics.drawable import GradientDrawable, InsetDrawable, LayerDrawable

    native = widget._impl.native

    def ring(color, border, width, inset):
        oval = GradientDrawable()
        oval.setShape(GradientDrawable.OVAL)
        oval.setColor(_color(color) if color else 0)
        oval.setStroke(_dp(native, width), _color(border))
        return InsetDrawable(oval, _dp(native, inset))

    native.setBackground(LayerDrawable([ring(None, glow, 5, 0), ring(fill, stroke, 2.5, 6)]))
    native.setGravity(17)  # Gravity.CENTER
    native.setSingleLine(True)
    return True


def letter_spacing(widget: toga.Widget, em: float):
    if IS_ANDROID:
        widget._impl.native.setLetterSpacing(em)


def tint(widget: toga.Widget, color: str, off: str | None = None):
    """Accent color for text fields, dropdowns, switches and progress bars."""
    if not IS_ANDROID:
        return
    from android import R
    from android.content.res import ColorStateList

    native = widget._impl.native
    on = ColorStateList.valueOf(_color(color))
    if off is not None:  # a Switch: color the thumb and track by state
        checked = ColorStateList([[R.attr.state_checked], []], [_color(color), _color(off)])
        native.setThumbTintList(checked)
        native.setTrackTintList(checked)
    elif hasattr(native, "setProgressTintList"):
        native.setProgressTintList(on)
        native.setIndeterminateTintList(on)
    else:
        native.setBackgroundTintList(on)


_listener_classes = {}


def on_tap(widget: toga.Widget, handler: Callable[[], None], long_press: bool = False) -> bool:
    """Make any widget (a Box row, say) respond to taps."""
    if not IS_ANDROID:
        return False
    from android.view import View
    from java import dynamic_proxy

    if not _listener_classes:

        class Tap(dynamic_proxy(View.OnClickListener)):
            def __init__(self, handler):
                super().__init__()
                self.handler = handler

            def onClick(self, view):
                self.handler()

        class LongTap(dynamic_proxy(View.OnLongClickListener)):
            def __init__(self, handler):
                super().__init__()
                self.handler = handler

            def onLongClick(self, view):
                self.handler()
                return True

        _listener_classes.update(tap=Tap, long=LongTap)

    native = widget._impl.native
    listener = _listener_classes["long" if long_press else "tap"](handler)
    if long_press:
        native.setOnLongClickListener(listener)
    else:
        native.setOnClickListener(listener)
    return True


def toast(app: toga.App, text: str) -> bool:
    """A short native notification at the bottom of the screen."""
    if not IS_ANDROID:
        return False
    from android.widget import Toast

    Toast.makeText(app._impl.native, text, Toast.LENGTH_SHORT).show()
    return True


class NativeList:
    """A recycling Android ListView inside a Toga Box, for long leaderboards.

    Toga widgets cost dozens of Java calls each, so a Box per row takes
    seconds for a few hundred songs. A ListView only builds the rows on
    screen and reuses them while scrolling. Every Python->Java call is
    slow on a phone, so binding a row is kept to a handful: each text view
    gets its colors and sizes from one ``Html.fromHtml`` string, and a
    row's rounded background is only rebuilt when its kind changes.

    ``backgrounds`` maps a row kind to ``(fill, stroke)`` (stroke may be
    None). Each row is a dict with ``kind`` and three HTML strings:
    ``rank``, ``info`` and ``score``.
    """

    def __init__(self, box: toga.Box, on_select: Callable[[int], None], backgrounds: dict, ripple: str):
        from android.content.res import ColorStateList
        from android.graphics import Color
        from android.graphics.drawable import ColorDrawable, GradientDrawable, RippleDrawable
        from android.text import Html
        from android.util import TypedValue
        from android.view import Gravity, View, ViewGroup
        from android.widget import AdapterView, LinearLayout, ListAdapter, ListView, RelativeLayout, TextView
        from java import dynamic_proxy

        self.rows: list[dict] = []
        activity = box._impl._native_activity
        native = box._impl.native
        owner = self
        holders = {}  # row view hashCode -> [rank, info, score, kind]
        ripple_color = ColorStateList.valueOf(_color(ripple))
        radius, stroke_px = _dp(native, 12), _dp(native, 1)
        html_mode = Html.FROM_HTML_MODE_LEGACY
        wrap = ViewGroup.LayoutParams.WRAP_CONTENT

        def background(kind):
            fill, stroke = backgrounds[kind]
            shape = GradientDrawable()
            shape.setColor(_color(fill))
            shape.setCornerRadius(radius)
            if stroke:
                shape.setStroke(stroke_px, _color(stroke))
            return RippleDrawable(ripple_color, shape, None)

        def text_view(size, gravity):
            tv = TextView(activity)
            tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, size)
            tv.setGravity(gravity)
            return tv

        def build_row():
            row = LinearLayout(activity)
            row.setOrientation(LinearLayout.HORIZONTAL)
            row.setGravity(Gravity.CENTER_VERTICAL)
            row.setPadding(_dp(native, 14), _dp(native, 12), _dp(native, 14), _dp(native, 12))
            rank = text_view(15, Gravity.START)
            rank.setMinWidth(_dp(native, 52))
            info = text_view(16, Gravity.START)
            score = text_view(16, Gravity.END)
            row.addView(rank, LinearLayout.LayoutParams(wrap, wrap))
            row.addView(info, LinearLayout.LayoutParams(0, wrap, 1.0))  # takes the free width
            row.addView(score, LinearLayout.LayoutParams(wrap, wrap))
            holders[row.hashCode()] = [rank, info, score, None]
            return row

        class Adapter(dynamic_proxy(ListAdapter)):
            def getCount(self):
                return len(owner.rows)

            def getItem(self, position):
                return None

            def getItemId(self, position):
                return position

            def hasStableIds(self):
                return False

            def getView(self, position, convert_view, parent):
                row = convert_view if convert_view is not None else build_row()
                holder = holders[row.hashCode()]
                data = owner.rows[position]
                holder[0].setText(Html.fromHtml(data["rank"], html_mode))
                holder[1].setText(Html.fromHtml(data["info"], html_mode))
                holder[2].setText(Html.fromHtml(data["score"], html_mode))
                if holder[3] != data["kind"]:
                    holder[3] = data["kind"]
                    row.setBackground(background(data["kind"]))
                return row

            def getItemViewType(self, position):
                return 0

            def getViewTypeCount(self):
                return 1

            def isEmpty(self):
                return not owner.rows

            def areAllItemsEnabled(self):
                return True

            def isEnabled(self, position):
                return True

            def registerDataSetObserver(self, observer):
                pass

            def unregisterDataSetObserver(self, observer):
                pass

            def getAutofillOptions(self):
                return None

        class Click(dynamic_proxy(AdapterView.OnItemClickListener)):
            def onItemClick(self, parent, view, position, row_id):
                on_select(position)

        self._adapter_class = Adapter
        self.view = ListView(activity)
        self.view.setDivider(ColorDrawable(Color.TRANSPARENT))
        self.view.setDividerHeight(_dp(native, 6))
        self.view.setSelector(ColorDrawable(Color.TRANSPARENT))
        self.view.setOverScrollMode(View.OVER_SCROLL_NEVER)
        self.view.setOnItemClickListener(Click())
        match = RelativeLayout.LayoutParams.MATCH_PARENT
        native.addView(self.view, RelativeLayout.LayoutParams(match, match))

    def set_rows(self, rows: list[dict]):
        self.rows = rows
        # A fresh adapter makes the ListView reload everything and scroll to the top
        self.view.setAdapter(self._adapter_class())


def style_window(app: toga.App, bar: str, subtitle: str | None = None) -> bool:
    """Color the action bar and system bars to match the app."""
    if not IS_ANDROID:
        return False
    from android.graphics.drawable import ColorDrawable

    activity = app._impl.native
    action_bar = activity.getSupportActionBar()
    if action_bar is not None:
        action_bar.setBackgroundDrawable(ColorDrawable(_color(bar)))
        action_bar.setElevation(0)
        action_bar.setSubtitle(subtitle)
    window = activity.getWindow()
    window.setStatusBarColor(_color(bar))
    window.setNavigationBarColor(_color(bar))
    return True


def make_player():
    return AndroidPlayer() if IS_ANDROID else NullPlayer()


# ---------- Files ----------
#
# Android apps can't browse the file system freely. The Storage Access
# Framework lets the user pick a location (Downloads, Google Drive...) and
# hands back a content:// URI we can read or write.


def _start_activity(app: toga.App, intent) -> asyncio.Future:
    """Start an Android activity; the future gets the result Intent (or None)."""
    from android.app import Activity

    future = asyncio.get_running_loop().create_future()

    def on_complete(code, data):
        if not future.done():
            future.set_result(data if code == Activity.RESULT_OK else None)

    app._impl.start_activity(intent, on_complete=on_complete)
    return future


def _display_name(resolver, uri) -> str:
    from android.provider import OpenableColumns

    name = ""
    cursor = resolver.query(uri, None, None, None, None)
    if cursor is not None:
        try:
            if cursor.moveToFirst():
                name = cursor.getString(cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)) or ""
        finally:
            cursor.close()
    return name or uri.getLastPathSegment() or "Imported"


def _read_stream(stream) -> bytes:
    from java import jarray, jbyte

    buf = jarray(jbyte)(65536)
    chunks = []
    try:
        while (n := stream.read(buf)) != -1:
            chunks.append(bytes(buf)[:n])
    finally:
        stream.close()
    return b"".join(chunks)


async def open_document(app: toga.App, title: str, extension: str) -> tuple[str, bytes] | None:
    """Let the user pick a file. Returns (file name, contents), or None if cancelled."""
    if not IS_ANDROID:
        path = await app.main_window.dialog(toga.OpenFileDialog(title, file_types=[extension]))
        return (Path(path).name, Path(path).read_bytes()) if path else None

    from android.content import Intent

    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")  # JSON files often have no reliable MIME type
    data = await _start_activity(app, intent)
    if data is None or data.getData() is None:
        return None
    uri = data.getData()
    resolver = app._impl.native.getContentResolver()
    return _display_name(resolver, uri), _read_stream(resolver.openInputStream(uri))


async def save_document(app: toga.App, title: str, filename: str, mime: str, content: bytes) -> str | None:
    """Let the user choose where to save ``content``. Returns the name saved to, or None."""
    if not IS_ANDROID:
        ext = Path(filename).suffix.lstrip(".")
        path = await app.main_window.dialog(
            toga.SaveFileDialog(title, suggested_filename=filename, file_types=[ext])
        )
        if not path:
            return None
        Path(path).write_bytes(content)
        return str(path)

    from android.content import Intent

    intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType(mime)
    intent.putExtra(Intent.EXTRA_TITLE, filename)
    data = await _start_activity(app, intent)
    if data is None or data.getData() is None:
        return None
    uri = data.getData()
    resolver = app._impl.native.getContentResolver()
    stream = resolver.openOutputStream(uri)
    try:
        stream.write(content)
    finally:
        stream.close()
    return _display_name(resolver, uri)
