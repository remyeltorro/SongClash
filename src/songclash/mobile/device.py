"""Android services (audio, file picking), with desktop fallbacks.

The Android parts talk to Java through Chaquopy, which Briefcase bundles.
On a desktop (``python -m songclash.mobile``) Toga's file dialogs are used
and audio previews are unavailable.
"""

from __future__ import annotations

import asyncio
import contextlib
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
        listener = self._Listener(self.generation, on_started, on_finished)
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


def tune_button(button: toga.Button):
    """Android buttons default to ALL CAPS and an 88dp minimum width, which
    shouts song titles and pushes a row of five buttons off the screen."""
    if not IS_ANDROID:
        return
    native = button._impl.native
    native.setAllCaps(False)
    native.setMinWidth(0)
    native.setMinimumWidth(0)
    pad = int(6 * native.getResources().getDisplayMetrics().density)
    native.setPadding(pad, native.getPaddingTop(), pad, native.getPaddingBottom())


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
