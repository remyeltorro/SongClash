"""30-second audio previews: lookup on iTunes, playback, and button state."""

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from songclash.services import itunes
from songclash.ui.tasks import Task

VOLUME = 0.7


class AudioPreview(QObject):
    """Plays one preview at a time on one of the battle panels.

    ``panels`` maps a side ("A"/"B") to its BattlePanel. Preview URLs found
    on iTunes are cached on the song dict (``preview_url``) so they are saved
    with the session.
    """

    message = pyqtSignal(str)

    def __init__(self, panels, runner, parent=None):
        super().__init__(parent)
        self.panels = panels
        self.runner = runner
        self.active_side = None
        self.pending = None  # (song key, side) being looked up
        self.no_preview = set()  # songs iTunes had no preview for, this run

        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.output.setVolume(VOLUME)
        self.player.setAudioOutput(self.output)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.mediaStatusChanged.connect(self._on_status_changed)
        self.player.errorOccurred.connect(self._on_error)

    def toggle(self, side, key, song):
        """Play ``song`` on ``side``, or stop if that side is already playing."""
        if self.active_side == side:
            self.stop()
            return
        if not song or self.pending == (key, side):
            return
        if song.get("preview_url"):
            self.play_url(song["preview_url"], side)
            return
        if key in self.no_preview:
            self._flash_not_found(side)
            return

        self.pending = (key, side)
        self.panels[side].set_audio_text("⏳ Loading...")
        task = Task(itunes.find_preview, song["artist"], song["title"], song["album"])
        self.runner.run(
            task,
            lambda url: self.on_found(key, side, url, song),
            lambda err: self.on_lookup_failed(key, side, err),
        )

    def forget_misses(self):
        """Allow songs without a preview to be looked up again."""
        self.no_preview.clear()

    def _take_pending(self, key, side):
        """True if this lookup is still wanted.

        ``stop()`` (called whenever the matchup changes) clears ``pending``,
        so results for songs no longer on screen are dropped.
        """
        if self.pending != (key, side):
            return False
        self.pending = None
        return True

    def on_found(self, key, side, url, song=None):
        if song is not None:
            if url:
                song["preview_url"] = url
            else:
                self.no_preview.add(key)
        if not self._take_pending(key, side):
            return
        if url:
            self.play_url(url, side)
        else:
            self._flash_not_found(side)

    def on_lookup_failed(self, key, side, err):
        if self._take_pending(key, side):
            self.panels[side].set_audio_idle()
            self.message.emit(f"Preview lookup failed: {err}")

    def _flash_not_found(self, side):
        panel = self.panels[side]
        panel.set_audio_text("✖ No Preview Found")
        self.message.emit("No preview available for this song.")
        QTimer.singleShot(2000, lambda: self.active_side != side and panel.set_audio_idle())

    def play_url(self, url, side):
        self.stop()
        self.active_side = side
        self.panels[side].set_audio_playing()
        self.player.setSource(QUrl(url))
        self.player.play()

    def stop(self):
        self.player.stop()
        self.pending = None
        self.active_side = None
        for panel in self.panels.values():
            panel.set_audio_idle()

    def _on_position_changed(self, position):
        duration = self.player.duration()
        if self.active_side and duration > 0:
            progress = self.panels[self.active_side].progress
            progress.setMaximum(duration)
            progress.setValue(position)

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop()

    def _on_error(self, _error, message):
        self.stop()
        self.message.emit(f"Could not play preview: {message}")
