"""Modal dialogs: import options, artist picker, manual song entry."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from songclash.services.musicbrainz import SECONDARY_TYPES

# Options handled specially by the importer (not MusicBrainz secondary types)
EXTRA_TYPES = ["EP", "Bootleg"]


def _ok_cancel(dialog):
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class ImportOptionsDialog(QDialog):
    """Choose which kinds of releases to include when importing an artist."""

    def __init__(self, parent=None, checked=()):
        super().__init__(parent)
        self.setWindowTitle("Import Options")
        layout = QVBoxLayout(self)

        lbl = QLabel("Studio albums are always included.\nAlso include:")
        lbl.setObjectName("dialogHeading")
        layout.addWidget(lbl)

        self.checkboxes = {}
        for name in EXTRA_TYPES + SECONDARY_TYPES:
            cb = QCheckBox(name)
            cb.setChecked(name in checked)
            self.checkboxes[name] = cb
            layout.addWidget(cb)

        layout.addStretch()
        layout.addWidget(_ok_cancel(self))

    def checked(self):
        return [name for name, cb in self.checkboxes.items() if cb.isChecked()]


class ArtistPickerDialog(QDialog):
    """Pick the right artist among MusicBrainz search results."""

    def __init__(self, artists, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Artist")
        self.resize(620, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Several artists match. Which one did you mean?"))

        self.list = QListWidget()
        for a in artists:
            details = ", ".join(x for x in (a["disambiguation"], a["type"], a["country"], a["begin"]) if x)
            item = QListWidgetItem(f"{a['name']}  ({details})" if details else a["name"])
            item.setData(Qt.ItemDataRole.UserRole, a)
            item.setToolTip(item.text())
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list)

        layout.addWidget(_ok_cancel(self))

    def selected(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class AddSongDialog(QDialog):
    """Enter a song by hand (for tracks MusicBrainz doesn't list)."""

    def __init__(self, parent=None, predefined_artist=None, existing_albums=None, album=""):
        super().__init__(parent)
        self.setWindowTitle("Add Manual Song")
        self.resize(400, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Enter song title...")
        form.addRow("Title:", self.inp_title)

        self.inp_artist = QLineEdit(predefined_artist or "")
        form.addRow("Artist:", self.inp_artist)

        self.inp_album = QComboBox()
        self.inp_album.setEditable(True)
        self.inp_album.addItems(existing_albums or [])
        if album:
            self.inp_album.setCurrentText(album)
        form.addRow("Album:", self.inp_album)

        self.inp_year = QLineEdit()
        self.inp_year.setPlaceholderText("YYYY")
        self.inp_year.setMaxLength(4)
        form.addRow("Year:", self.inp_year)

        layout.addLayout(form)
        layout.addStretch()

        self.buttons = _ok_cancel(self)
        layout.addWidget(self.buttons)

        # A title is required
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText("Add Song")
        ok.setEnabled(False)
        self.inp_title.textChanged.connect(lambda t: ok.setEnabled(bool(t.strip())))

    def get_data(self):
        return {
            "title": self.inp_title.text().strip(),
            "artist": self.inp_artist.text().strip(),
            "album": self.inp_album.currentText().strip(),
            "year": self.inp_year.text().strip(),
        }
