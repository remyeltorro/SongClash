"""Application entry point: creates the QApplication and the main window."""

import contextlib
import logging
import os
import sys
import traceback

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from songclash import APP_ID, APP_NAME, __version__
from songclash.resources import APP_ICON
from songclash.ui import theme
from songclash.ui.main_window import MainWindow

log = logging.getLogger(__name__)


def install_excepthook(window_getter):
    """Show unexpected errors instead of letting PyQt abort the app."""

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("Unhandled exception:\n%s", text)
        box = QMessageBox(window_getter())
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unexpected Error")
        box.setText(f"Something went wrong: {exc}\n\nYou may want to save your session.")
        box.setDetailedText(text)
        box.exec()

    sys.excepthook = hook


def _set_windows_app_id():
    if sys.platform != "win32":
        return
    import ctypes

    with contextlib.suppress(AttributeError, OSError):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def main():
    # stderr is None in a --windowed PyInstaller exe
    if sys.stderr is not None:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(APP_ICON)))
    theme.apply(app)

    window = MainWindow()
    install_excepthook(lambda: window)
    window.show()
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        window.open_file(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
