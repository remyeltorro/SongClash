"""The "Add Artist" flow: search, disambiguate, choose release types, fetch."""

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QInputDialog, QMessageBox, QProgressDialog

from songclash.services import musicbrainz
from songclash.ui.dialogs import ArtistPickerDialog, ImportOptionsDialog
from songclash.ui.tasks import Task


class ArtistImporter(QObject):
    """Walks the user through importing an artist from MusicBrainz.

    Emits ``imported(artist_name, songs)`` with the fetched song dicts.
    """

    imported = pyqtSignal(str, list)

    def __init__(self, parent_widget, runner, settings):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.runner = runner
        self.settings = settings

    def start(self):
        name, ok = QInputDialog.getText(self.parent_widget, "Add Artist", "Artist name:")
        name = name.strip()
        if not ok or not name:
            return
        task = Task(musicbrainz.search_artists, name)
        dlg = self._progress_dialog(f"Searching MusicBrainz for '{name}'...", task)
        self.runner.run(
            task,
            lambda artists: self._on_artists_found(name, artists),
            lambda err: QMessageBox.warning(self.parent_widget, "Search Failed", err),
        )
        dlg.show()

    def _on_artists_found(self, query, artists):
        artist = self._choose_artist(query, artists)
        if artist is None:
            return
        options = ImportOptionsDialog(self.parent_widget, self.settings.import_types())
        if options.exec() != QDialog.DialogCode.Accepted:
            return
        checked = options.checked()
        self.settings.set_import_types(checked)
        self._fetch(artist, checked)

    def _choose_artist(self, query, artists):
        if not artists:
            QMessageBox.information(self.parent_widget, "Add Artist", f"No artist found for '{query}'.")
            return None
        exact = [a for a in artists if a["name"].casefold() == query.casefold()]
        if len(exact) == 1:
            return exact[0]
        picker = ArtistPickerDialog(artists, self.parent_widget)
        if picker.exec() != QDialog.DialogCode.Accepted:
            return None
        return picker.selected()

    def _fetch(self, artist, checked):
        task = Task(
            musicbrainz.fetch_discography,
            artist["id"],
            artist["name"],
            **musicbrainz.discography_options(checked),
        ).with_progress()
        dlg = self._progress_dialog(f"Fetching songs for {artist['name']}...", task)

        def on_progress(msg, pct):
            dlg.setLabelText(msg)
            if pct < 0:
                dlg.setRange(0, 0)
            else:
                dlg.setRange(0, 100)
                dlg.setValue(pct)

        task.progress.connect(on_progress)
        self.runner.run(
            task,
            lambda songs: self.imported.emit(artist["name"], songs),
            lambda err: QMessageBox.warning(self.parent_widget, "Fetch Failed", err),
        )
        dlg.show()

    def _progress_dialog(self, text, task):
        dlg = QProgressDialog(text, "Cancel", 0, 0, self.parent_widget)
        dlg.setWindowTitle("Please Wait")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.setMinimumWidth(380)
        dlg.canceled.connect(task.cancel)
        # Connected before the result handlers, so it closes before they run
        for sig in (task.succeeded, task.failed, task.done):
            sig.connect(dlg.close)
        return dlg
