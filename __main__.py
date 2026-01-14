import sys
import json
import random
import os
import requests
import re
from collections import deque

# import musicbrainzngs # Removed dependency
from youtubesearchpython import VideosSearch

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QProgressBar,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QInputDialog,
    QFileDialog,
    QAbstractItemView,
    QComboBox,
    QSizePolicy,
    QProgressDialog,
    QLineEdit,
    QFormLayout,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QStandardPaths, QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap, QDesktopServices, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkDiskCache


# ==========================================
# 0. CUSTOM WIDGETS
# ==========================================
class SongCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        # Layout to center label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        # Inherit font style from stylesheet or set explicitly if needed
        # We start with transparent bg so the Frame bg shows
        self.label.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.label)

        # Styles
        # Note: We use ID selector or just class selector logic if we could,
        # but here we update the whole sheet.
        self.default_style = """
            SongCard {
                background-color: #3d3d3d; 
                border-radius: 12px;
                border: 2px solid #444;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: #eee;
                background: transparent;
                border: none;
            }
        """
        self.hover_style = """
            SongCard {
                background-color: #4a4a4a;
                border-radius: 12px;
                border: 2px solid #5a9fd4;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: white;
                background: transparent;
                border: none;
            }
        """
        self.pressed_style = """
            SongCard {
                background-color: #2a2a2a;
                border-radius: 12px;
                border: 2px solid #3498db;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: white;
                background: transparent;
                border: none;
            }
        """
        self.disabled_style = """
            SongCard {
                background-color: #222;
                border-radius: 12px;
                border: 2px solid #333;
            }
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: #555;
            }
        """

        self.setStyleSheet(self.default_style)

    def setText(self, text):
        self.label.setText(text)

    def enterEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.setStyleSheet(self.default_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet(self.pressed_style)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.pos()):
                self.clicked.emit()
                self.setStyleSheet(self.hover_style)
            else:
                self.setStyleSheet(self.default_style)
        super().mouseReleaseEvent(event)

    def setEnabled(self, validate):
        super().setEnabled(validate)
        if validate:
            self.setStyleSheet(self.default_style)
        else:
            self.setStyleSheet(self.disabled_style)


# ==========================================
# 0b. DIALOGS
# ==========================================
class AlbumTypeSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Album Types to Import")
        self.resize(300, 400)
        self.setStyleSheet("background-color: #333; color: white;")

        layout = QVBoxLayout(self)

        lbl = QLabel(
            "Select album types to INCLUDE:\n(Unchecked types will be rejected)"
        )
        lbl.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl)

        # Common secondary types
        self.types = [
            "Live",
            "Compilation",
            "Remix",
            "Soundtrack",
            "Spokenword",
            "Interview",
            "Audio drama",
            "Demo",
            "Audiobook",
            "Bootleg",
        ]

        self.checkboxes = {}

        # Default: All Unchecked (Strict mode)
        # Checkbox means "Include"
        for t in self.types:
            import PyQt6.QtWidgets as QtWidgets

            cb = QtWidgets.QCheckBox(t)
            cb.setStyleSheet("padding: 5px;")
            self.checkboxes[t] = cb
            layout.addWidget(cb)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet(
            "background-color: #3498db; padding: 8px; border-radius: 4px;"
        )

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(
            "background-color: #555; padding: 8px; border-radius: 4px;"
        )

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_reject_list(self):
        """Returns list of types that are NOT checked (i.e. to be rejected)."""
        rejects = []
        for t, cb in self.checkboxes.items():
            if not cb.isChecked():
                rejects.append(t)
        return rejects


class AddSongDialog(QDialog):
    def __init__(self, parent=None, predefined_artist=None, existing_albums=None):
        super().__init__(parent)
        self.setWindowTitle("Add Manual Song")
        self.resize(400, 250)
        self.setStyleSheet("background-color: #333; color: white;")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Styles
        input_style = (
            "padding: 5px; background: #444; border: 1px solid #555; color: white;"
        )

        # Title
        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Enter song title...")
        self.inp_title.setStyleSheet(input_style)
        form.addRow("Title:", self.inp_title)

        # Artist
        self.inp_artist = QLineEdit()
        self.inp_artist.setStyleSheet(input_style)
        if predefined_artist:
            self.inp_artist.setText(predefined_artist)
        form.addRow("Artist:", self.inp_artist)

        # Album
        self.inp_album = QComboBox()
        self.inp_album.setEditable(True)
        self.inp_album.setStyleSheet(input_style)
        if existing_albums:
            self.inp_album.addItems(existing_albums)
        form.addRow("Album:", self.inp_album)

        # Year
        self.inp_year = QLineEdit()
        self.inp_year.setPlaceholderText("YYYY")
        self.inp_year.setStyleSheet(input_style)
        form.addRow("Year:", self.inp_year)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Add Song")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet(
            "background-color: #3498db; padding: 8px; border-radius: 4px; font-weight: bold;"
        )

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(
            "background-color: #555; padding: 8px; border-radius: 4px;"
        )

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "title": self.inp_title.text().strip(),
            "artist": self.inp_artist.text().strip(),
            "album": self.inp_album.currentText().strip(),
            "year": self.inp_year.text().strip(),
        }


# ==========================================
# 1. DATABASE MANAGER (With Filtering)
# ==========================================
class RankingSession:
    def __init__(self):
        self.songs = {}
        self.current_filename = None
        self.has_unsaved_changes = False
        self.active_filter = "All Albums"  # Default filter
        self.match_history = deque(maxlen=20)  # Track last 20 pairings to avoid repeats

    def new_session(self):
        self.songs = {}
        self.current_filename = None
        self.has_unsaved_changes = False
        self.active_filter = "All Albums"
        self.match_history.clear()

    def load_from_file(self, filepath):
        try:
            with open(filepath, "r") as f:
                self.songs = json.load(f)
            self.current_filename = filepath
            self.has_unsaved_changes = False
            self.match_history.clear()
            return True, f"Loaded {len(self.songs)} songs."
        except Exception as e:
            return False, str(e)

    def save_session(self, filepath=None):
        target = filepath if filepath else self.current_filename
        if not target:
            return False, "No filename specified"
        try:
            with open(target, "w") as f:
                json.dump(self.songs, f, indent=4)
            self.current_filename = target
            self.has_unsaved_changes = False
            return True, "Saved successfully."
        except Exception as e:
            return False, str(e)

    def merge_data(self, new_data):
        count = 0
        for title, data in new_data.items():
            if title not in self.songs:
                self.songs[title] = data
                count += 1
        if count > 0:
            self.has_unsaved_changes = True
        return count

    def get_albums_list(self):
        """Returns a sorted list of unique albums in the current database."""
        albums = set()
        for data in self.songs.values():
            if "album" in data:
                albums.add(data["album"])
        return sorted(list(albums))

    def get_filtered_keys(self):
        """Returns list of song keys matching the current filter."""
        if self.active_filter == "All Albums":
            return list(self.songs.keys())

        filtered = []
        for title, data in self.songs.items():
            if data.get("album") == self.active_filter:
                filtered.append(title)
        return filtered

    def get_matchup(self):
        candidates = self.get_filtered_keys()
        if len(candidates) < 2:
            return None

        # --- SMART MATCHMAKING ---

        # 1. Select Song A (Challenger)
        # Prioritize songs with fewer matches to ensure even coverage.

        # Sort candidates by match count (ascending), then randomize slightly to break ties
        random.shuffle(candidates)
        candidates.sort(key=lambda k: self.songs[k]["matches"])

        pool_size = max(2, len(candidates) // 4)  # Bottom 25%
        pool_a = candidates[:pool_size]

        song_a = random.choice(pool_a)
        score_a = self.songs[song_a]["score"]

        # 2. Select Song B (Opponent)
        # Prioritize songs with similar ELO ratings for a fair fight.
        # Also avoid recent matchups.

        opponents = [k for k in candidates if k != song_a]

        weights = []
        valid_opponents = []

        for opp in opponents:
            # Check history
            pair_key = tuple(sorted((song_a, opp)))
            if pair_key in self.match_history:
                continue  # Skip recently matched pairs

            score_b = self.songs[opp]["score"]
            diff = abs(score_a - score_b)

            # Weight formula: Higher weight for smaller difference
            # Add base to avoid division by zero and give small chance to upsets
            weight = 1000 / (diff + 50)

            valid_opponents.append(opp)
            weights.append(weight)

        # Fallback if all opponents are in history (unlikely unless very few songs)
        if not valid_opponents:
            valid_opponents = opponents
            weights = [1] * len(opponents)

        song_b = random.choices(valid_opponents, weights=weights, k=1)[0]

        # Record history
        self.match_history.append(tuple(sorted((song_a, song_b))))

        # Return shuffled pair so A isn't always on the left
        pair = [song_a, song_b]
        random.shuffle(pair)
        return pair

    def update_score(self, winner, loser):
        k = 32
        r_win = self.songs[winner]["score"]
        r_los = self.songs[loser]["score"]

        e_win = 1 / (1 + 10 ** ((r_los - r_win) / 400))
        e_los = 1 / (1 + 10 ** ((r_win - r_los) / 400))

        self.songs[winner]["score"] = r_win + k * (1 - e_win)
        self.songs[loser]["score"] = r_los + k * (0 - e_los)
        self.songs[winner]["matches"] += 1
        self.songs[loser]["matches"] += 1
        self.has_unsaved_changes = True


# ==========================================
# 2. WORKER THREADS
# ==========================================
class Worker(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str, int)  # New signal: (message, progress_value)

    def __init__(self, task, payload, reject_list=None):
        super().__init__()
        self.task = task
        self.payload = payload
        self.reject_list = reject_list
        self.process = None  # Handle to subprocess
        self._is_running = True

    def stop(self):
        """Force kills the subprocess if it exists."""
        self._is_running = False
        if self.process:
            try:
                print(f"Terminating worker subprocess for task: {self.task}")
                self.process.terminate()
                # Give it a moment to die gracefully
                try:
                    import subprocess

                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception as e:
                print(f"Error killing subprocess: {e}")

    def run(self):
        if self.task == "fetch_artist":
            self.fetch_artist_songs()
        elif self.task == "find_video":
            self.search_youtube()
        elif self.task == "find_audio":
            self.search_itunes()

    def fetch_artist_songs(self):
        import subprocess

        artist_name = self.payload
        print(f"Searching {artist_name} (Subprocess)...")

        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fetch_data.py"
        )

        try:
            # Prepare arguments
            if getattr(sys, "frozen", False):
                # We are running in a bundle
                # Call myself with --worker flag
                cmd_args = [sys.executable, "--worker", artist_name]
            else:
                # Normal script execution
                script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "fetch_data.py"
                )
                cmd_args = [sys.executable, script_path, artist_name]

            # If we have a reject list, pass it as the 3rd argument (comma-separated)
            if self.reject_list:
                cmd_args.append(",".join(self.reject_list))
            elif self.reject_list is not None and len(self.reject_list) == 0:
                # Pass empty string explicitly if list is empty but provided (implied 'reject nothing')
                cmd_args.append("")

            # Use Popen to read output line by line
            self.process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            output_json = []

            while self._is_running:
                # Read line from stdout
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break

                if line:
                    # Keep original line for JSON, but strip for checking tags
                    stripped = line.strip()

                    # Check for progress tag
                    if stripped.startswith("PROGRESS:"):
                        # Format: PROGRESS: Current/Total - Album Name
                        try:
                            parts = stripped.split(" - ", 1)
                            album = parts[1] if len(parts) > 1 else ""
                            nums = parts[0].replace("PROGRESS:", "").strip().split("/")
                            current = int(nums[0])
                            total = int(nums[1])

                            percent = int((current / total) * 100)
                            self.progress.emit(
                                f"Fetching: {album} ({current}/{total})", percent
                            )
                        except Exception as e:
                            print(f"Progress parse error: {e}")

                    # Check for status tag (simple message update)
                    elif stripped.startswith("STATUS:"):
                        msg = stripped.replace("STATUS:", "").strip()
                        # emit -1 for indeterminate
                        self.progress.emit(msg, -1)

                    else:
                        # Assume it's part of the JSON output
                        # We append the ORIGINAL line to preserve structure if needed (though json.loads handles whitespace)
                        output_json.append(line)

            # Wait for finish
            stdout_remainder, stderr_output = self.process.communicate()
            if stdout_remainder:
                # Append any remainder that isn't progress (unlikely given logic above but good safety)
                # Filter both PROGRESS and STATUS
                rem_stripped = stdout_remainder.strip()
                if not rem_stripped.startswith(
                    "PROGRESS:"
                ) and not rem_stripped.startswith("STATUS:"):
                    output_json.append(stdout_remainder)

            if self.process.returncode != 0:
                # If we killed it manually, don't scream error
                if not self._is_running:
                    return

                print(f"Subprocess failed: {stderr_output}")
                self.finished.emit({})
                return

            if stderr_output:
                print(f"[Fetcher Log]: {stderr_output}")

            full_output = "".join(output_json)
            if not full_output:
                self.finished.emit({})
                return

            try:
                # Sometimes progress lines might get mixed if buffering is weird,
                # but we filter for lines starting with { usually or just parse the last valid json line
                # Ideally, the script only prints one JSON blob at the end.
                # Let's find the JSON blob really simply:
                match = re.search(r"(\{.*\})", full_output)
                if match:
                    new_songs = json.loads(match.group(1))
                    self.finished.emit(new_songs)
                else:
                    # Try direct load if pure json
                    try:
                        new_songs = json.loads(full_output)
                        self.finished.emit(new_songs)
                    except json.JSONDecodeError:
                        # Maybe the full output contains STATUS lines mixed in if they weren't caught line-by-line?
                        # Try to clean it up
                        cleaned_output = []
                        for line in full_output.splitlines():
                            if not line.startswith("STATUS:") and not line.startswith(
                                "PROGRESS:"
                            ):
                                cleaned_output.append(line)

                        new_songs = json.loads("".join(cleaned_output))
                        self.finished.emit(new_songs)

            except json.JSONDecodeError:
                # Fallback: maybe multiple lines of JSON?
                # Just emit empty if fail
                print("Failed to parse JSON output")
                self.finished.emit({})

        except Exception as e:
            print(f"Subprocess Execution Error: {e}")
            self.finished.emit({})

    def search_youtube(self):
        import subprocess

        p = self.payload
        query = f"{p['artist']} {p['title']}"

        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--worker", "youtube", query]
            else:
                script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "fetch_data.py"
                )
                cmd = [sys.executable, script_path, "youtube", query]

            # subprocess to run search
            # Use Popen instead of run() to allow killing
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            try:
                stdout, stderr = self.process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                stdout, stderr = self.process.communicate()
                print("YouTube search timed out")

            if self.process.returncode != 0:
                if not self._is_running:
                    return
                print(f"YouTube Subprocess Error: {stderr}")
                self.finished.emit(None)
                return

            url = stdout.strip()
            if url:
                self.finished.emit(url)
            else:
                self.finished.emit(None)

        except Exception as e:
            print(f"DEBUG: Youtube Subprocess Exception: {e}")
            self.finished.emit(None)

    def search_itunes(self):
        import subprocess

        p = self.payload
        # args: itunes artist song album
        try:
            if getattr(sys, "frozen", False):
                cmd = [
                    sys.executable,
                    "--worker",
                    "itunes",
                    p["artist"],
                    p["title"],
                    p["album"],
                ]
            else:
                script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "fetch_data.py"
                )
                cmd = [
                    sys.executable,
                    script_path,
                    "itunes",
                    p["artist"],
                    p["title"],
                    p["album"],
                ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )

            try:
                stdout, stderr = self.process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                stdout, stderr = self.process.communicate()

            url = stdout.strip()
            if url:
                self.finished.emit(url)
            else:
                self.finished.emit(None)

        except Exception as e:
            print(f"DEBUG: iTunes Subprocess Exception: {e}")
            self.finished.emit(None)


# ==========================================
# 3. GUI MAIN WINDOW
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = RankingSession()
        self.current_pair = None

        self.setWindowTitle("Ultimate Song Ranker")
        self.resize(1100, 300)
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")

        self.setup_menu()
        self.setup_ui()

        self.network_manager = QNetworkAccessManager()

        # Setup Disk Cache
        self.disk_cache = QNetworkDiskCache(self)
        cache_path = os.path.join(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.CacheLocation
            ),
            "ranksongs_images",
        )
        self.disk_cache.setCacheDirectory(cache_path)
        self.network_manager.setCache(self.disk_cache)

        self.network_manager.finished.connect(self.on_image_downloaded)

        # In-Memory Cache
        self.image_cache = {}
        self.active_downloads = {}

        self.update_status("Welcome.")
        self.toggle_battle_mode(False)
        QTimer.singleShot(0, self.center)

    def center(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        """Ensure all subprocesses are killed when the app closes."""
        print("Closing application, cleaning up workers...")
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        if hasattr(self, "y_worker") and self.y_worker and self.y_worker.isRunning():
            self.y_worker.stop()
            self.y_worker.wait()

        if hasattr(self, "a_worker") and self.a_worker and self.a_worker.isRunning():
            self.a_worker.stop()
            self.a_worker.wait()

        event.accept()

    def setup_menu(self):
        menu = self.menuBar()
        # Global stylesheet handles menu styling now
        # menu.setStyleSheet("background-color: #333; color: white;")

        file_menu = menu.addMenu("&File")

        # New Session
        act_new = QAction("New Session", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self.action_new)
        file_menu.addAction(act_new)

        # Open Session
        act_open = QAction("Open Session...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.action_open)
        file_menu.addAction(act_open)

        # Save
        act_save = QAction("Save", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.action_save)
        file_menu.addAction(act_save)

        # Save As
        act_save_as = QAction("Save As...", self)
        act_save_as.triggered.connect(self.action_save_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()

        # Merge
        act_merge = QAction("Import/Merge JSON...", self)
        act_merge.triggered.connect(self.action_merge_file)
        file_menu.addAction(act_merge)

        # Add Music Menu
        art_menu = menu.addMenu("&Add Music")

        # Add Artist
        act_add = QAction("Add Artist from Web...", self)
        act_add.setShortcut("Ctrl+F")
        act_add.triggered.connect(self.action_add_artist)
        art_menu.addAction(act_add)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)

        # TOP BAR: Filter + Status
        top_bar = QHBoxLayout()

        self.combo_filter = QComboBox()
        self.combo_filter.addItem("All Albums")
        self.combo_filter.setMinimumWidth(300)
        # self.combo_filter.setStyleSheet("padding: 5px; color: black; background: #ddd;")
        self.combo_filter.currentTextChanged.connect(self.on_filter_changed)

        self.lbl_session = QLabel("[Unsaved]")
        self.lbl_session.setStyleSheet("color: #b0b0b0; font-weight: bold;")

        top_bar.addWidget(QLabel("Filter:"))
        top_bar.addWidget(self.combo_filter)

        self.btn_delete_album = QPushButton("🗑")
        self.btn_delete_album.setToolTip("Delete currently selected album")
        self.btn_delete_album.setFixedSize(30, 30)
        self.btn_delete_album.setStyleSheet(
            "background-color: #e74c3c; color: white; border-radius: 4px; font-weight: bold;"
        )
        self.btn_delete_album.clicked.connect(self.delete_current_album)
        top_bar.addWidget(self.btn_delete_album)

        top_bar.addStretch()
        top_bar.addWidget(self.lbl_session)

        layout.addLayout(top_bar)

        # BATTLE AREA
        battle_layout = QHBoxLayout()
        self.panel_a = self.create_panel("A")
        # Give panels equal weight (stretch=4)
        battle_layout.addLayout(self.panel_a["layout"], 4)

        # Middle section with VS and Skip button
        middle_layout = QVBoxLayout()
        # Add stretch to center content vertically
        middle_layout.addStretch(1)

        vs = QLabel("VS")
        vs.setStyleSheet("font-size: 60px; font-weight: bold; color: #555;")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_layout.addWidget(vs)

        # Spacer between VS and Skip
        middle_layout.addSpacing(20)

        self.btn_skip = QPushButton("⏭ SKIP THIS MATCH")
        self.btn_skip.setFixedHeight(60)
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setStyleSheet(
            """
            QPushButton {
                background-color: #1a1a1a; 
                color: #888; 
                font-size: 16px; 
                font-weight: bold; 
                border-radius: 30px;
                padding: 10px 20px;
                border: 2px solid #333;
            }
            QPushButton:hover {
                background-color: #252525;
                color: #ccc;
                border-color: #555;
            }
            QPushButton:pressed {
                background-color: #111;
                color: #aaa;
            }
            """
        )
        self.btn_skip.clicked.connect(self.skip_matchup)
        middle_layout.addWidget(self.btn_skip)

        middle_layout.addStretch(1)

        # Middle gets less weight (stretch=1)
        battle_layout.addLayout(middle_layout, 1)

        self.panel_b = self.create_panel("B")
        battle_layout.addLayout(self.panel_b["layout"], 4)
        layout.addLayout(battle_layout)

        # VIDEO
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(350)
        self.web_view.setStyleSheet("background: black; border: 2px solid #444;")
        # layout.addWidget(self.web_view) # Hidden by request

        # Removed QWebEngineView for audio (codec issues)
        # Using Native QMediaPlayer
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Signals
        self.player.positionChanged.connect(self.on_audio_position_changed)
        self.player.durationChanged.connect(self.on_audio_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_audio_status_changed)

        # Adjust volume (optional, 70% is good default)
        self.audio_output.setVolume(0.7)

        # FOOTER
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)  # Center the button

        self.btn_leader = QPushButton("🏆  VIEW LEADERBOARD  🏆")
        self.btn_leader.clicked.connect(self.show_leaderboard)
        self.btn_leader.setFixedHeight(50)
        self.btn_leader.setMinimumWidth(300)
        self.btn_leader.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_leader.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db; 
                color: white; 
                border-radius: 25px; 
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4aa3df;
                margin-top: -2px; /* Slight lift effect */
            }
            QPushButton:pressed {
                background-color: #2980b9;
                margin-top: 2px;
            }
            """
        )
        btn_layout.addWidget(self.btn_leader)

        btn_layout.addSpacing(20)

        self.btn_album_leader = QPushButton("💿  ALBUM RANKINGS  💿")
        self.btn_album_leader.clicked.connect(self.show_album_leaderboard)
        self.btn_album_leader.setFixedHeight(50)
        self.btn_album_leader.setMinimumWidth(300)
        self.btn_album_leader.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_album_leader.setStyleSheet(
            """
            QPushButton {
                background-color: #8e44ad; 
                color: white; 
                border-radius: 25px; 
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #9b59b6;
                margin-top: -2px;
            }
            QPushButton:pressed {
                background-color: #71368a;
                margin-top: 2px;
            }
            """
        )
        btn_layout.addWidget(self.btn_album_leader)

        btn_layout.addStretch(1)  # Center the button
        layout.addLayout(btn_layout)

    def create_panel(self, side):
        l = QVBoxLayout()
        # Use our new SongCard which handles word wrapping and styling
        btn = SongCard(f"Song {side}")
        # Note: setFixedHeight is optional; removing it allows flex height for wrapped text
        # btn.setFixedHeight(80)
        btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        # But we might want constraints. Let's let layout stretch handle height,
        # or set a minimum height for presence.
        btn.setMinimumHeight(100)

        # Connect clicked signal
        btn.clicked.connect(lambda: self.vote(side))

        lbl = QLabel("")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #b0b0b0;")

        lbl_cover = QLabel()
        lbl_cover.setFixedSize(200, 200)
        lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_cover.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
        lbl_cover.setScaledContents(True)

        play = QPushButton("▶ Play Snippet")
        play.setStyleSheet(
            "color: #e74c3c; border: 1px solid #e74c3c; padding: 5px; border-radius: 4px;"
        )
        play.setCursor(Qt.CursorShape.PointingHandCursor)
        play.clicked.connect(lambda: self.play_video(side))

        btn_audio = QPushButton("♫ Audio Preview")
        btn_audio.setStyleSheet(
            "color: #e67e22; border: 1px solid #e67e22; padding: 5px; border-radius: 4px; margin-top: 5px;"
        )
        btn_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_audio.clicked.connect(lambda: self.play_audio_preview(side))

        l.addWidget(lbl_cover, 0, Qt.AlignmentFlag.AlignCenter)
        l.addWidget(btn)
        l.addWidget(lbl)

        # Audio Layout
        audio_layout = QVBoxLayout()
        audio_layout.setSpacing(0)

        # Progress Bar (Hidden by default)
        prog = QProgressBar()
        prog.setTextVisible(False)
        prog.setFixedHeight(5)
        prog.setStyleSheet(
            "QProgressBar { border: 0px; background: #444; border-radius: 2px; } QProgressBar::chunk { background: #e67e22; border-radius: 2px; }"
        )
        prog.setRange(0, 100)
        prog.setValue(0)
        prog.setVisible(False)

        audio_layout.addWidget(btn_audio)
        audio_layout.addWidget(prog)

        l.addLayout(audio_layout)

        # l.addWidget(play) # Hidden by request
        return {
            "layout": l,
            "btn": btn,
            "lbl": lbl,
            "play": play,
            "cover": lbl_cover,
            "audio_btn": btn_audio,
            "file": "",  # Keep track of which song is here
            "prog": prog,  # Audio Progress
        }

    # ==========================
    # LOGIC
    # ==========================
    def update_status(self, msg):
        name = (
            os.path.basename(self.session.current_filename)
            if self.session.current_filename
            else "[Unsaved]"
        )
        count = len(self.session.songs)
        mod = "*" if self.session.has_unsaved_changes else ""
        self.lbl_session.setText(f"{name}{mod} | Total Songs: {count} | {msg}")

    def refresh_filter_list(self, current_filter=None):
        """Re-populates the dropdown menu with available albums."""
        if current_filter is None:
            current_filter = self.combo_filter.currentText()
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        self.combo_filter.addItem("All Albums")

        albums = self.session.get_albums_list()
        self.combo_filter.addItems(albums)

        # Restore previous selection if possible
        idx = self.combo_filter.findText(current_filter)
        if idx != -1:
            self.combo_filter.setCurrentIndex(idx)
        else:
            self.combo_filter.setCurrentIndex(0)

        self.combo_filter.blockSignals(False)

    def on_filter_changed(self, text):
        self.session.active_filter = text
        self.next_matchup()

    def delete_current_album(self):
        album = self.combo_filter.currentText()
        if album == "All Albums":
            QMessageBox.warning(
                self,
                "Action Denied",
                "Cannot delete 'All Albums'. Please select a specific album to delete.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete ALL songs from the album:\n'{album}'?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete songs belonging to this album
            original_count = len(self.session.songs)

            # Iterate over copy of keys to allow deletion
            keys_to_delete = [
                k for k, v in self.session.songs.items() if v.get("album") == album
            ]

            for k in keys_to_delete:
                del self.session.songs[k]

            deleted_count = original_count - len(self.session.songs)

            self.session.has_unsaved_changes = True
            self.refresh_filter_list()
            # Reset filter to All Albums since the current one is gone
            self.combo_filter.setCurrentIndex(0)
            self.update_status(
                f"Deleted album '{album}' ({deleted_count} songs removed)."
            )
            self.next_matchup()

    def action_new(self):
        self.session.new_session()
        self.refresh_filter_list()
        self.toggle_battle_mode(False)
        self.update_status("New session.")

    def action_open(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if fname:
            ok, msg = self.session.load_from_file(fname)
            if ok:
                self.refresh_filter_list()
                self.toggle_battle_mode(True)
                self.next_matchup()
            self.update_status(msg)

    def action_save(self):
        if not self.session.current_filename:
            self.action_save_as()
        else:
            _, msg = self.session.save_session()
            self.update_status(msg)

    def action_save_as(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
        if fname:
            _, msg = self.session.save_session(fname)
            self.update_status(msg)

    def action_merge_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Merge", "", "JSON (*.json)")
        if fname:
            with open(fname, "r") as f:
                data = json.load(f)
            c = self.session.merge_data(data)
            self.refresh_filter_list()
            self.update_status(f"Merged {c} songs.")
            self.next_matchup()

    def action_add_artist(self):
        text, ok = QInputDialog.getText(self, "Add Artist", "Artist Name:")
        if ok and text:
            # Ask for types to include
            dlg = AlbumTypeSelectorDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            reject_list = dlg.get_reject_list()
            self.update_status(f"Fetching {text}...")

            # Progress Popup
            self.progress_dialog = QProgressDialog(
                f"Fetching songs for {text}...\nThis may take a few seconds.",
                "Cancel",
                0,
                100,
                self,
            )
            self.progress_dialog.setWindowTitle("Please Wait")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setAutoClose(
                False
            )  # Keep open until we explicitly close or finished

            # Style to center text and match app theme
            self.progress_dialog.resize(350, 150)
            self.progress_dialog.setStyleSheet(
                """
                QProgressDialog {
                    background-color: #2b2b2b;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-weight: bold;
                    qproperty-alignment: AlignCenter;
                }
                QProgressBar {
                    text-align: center;
                }
                QPushButton {
                    background-color: #555;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 4px;
                }
            """
            )

            self.progress_dialog.show()

            # Force alignment via object API to be sure
            for child in self.progress_dialog.findChildren(QLabel):
                child.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.worker = Worker("fetch_artist", text, reject_list)
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_added)

            # Connect cancel button to stop worker
            self.progress_dialog.canceled.connect(self.worker.stop)

            self.worker.start()

    def on_progress(self, msg, val):
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.setLabelText(msg)
            if val < 0:
                self.progress_dialog.setRange(0, 0)  # Indeterminate
            else:
                self.progress_dialog.setRange(0, 100)
                self.progress_dialog.setValue(val)

    def on_added(self, data):
        # Close progress popup
        if hasattr(self, "progress_dialog") and self.progress_dialog.isVisible():
            self.progress_dialog.close()

        if not data:
            self.update_status("Fetch failed.")
            return
        c = self.session.merge_data(data)
        self.refresh_filter_list()
        self.update_status(f"Added {c} songs.")
        self.toggle_battle_mode(True)
        self.next_matchup()

    def toggle_battle_mode(self, enable):
        for p in [self.panel_a, self.panel_b]:
            p["btn"].setEnabled(enable)
            p["play"].setEnabled(enable)
            p["audio_btn"].setEnabled(enable)
        self.btn_skip.setEnabled(enable)

    def next_matchup(self):
        pair = self.session.get_matchup()
        if not pair:
            # If filtering returns < 2 songs, disable buttons
            self.toggle_battle_mode(False)
            self.panel_a["btn"].setText("-")
            self.panel_b["btn"].setText("-")
            return

        self.toggle_battle_mode(True)
        self.current_pair = pair
        s_a, s_b = pair
        d_a, d_b = self.session.songs[s_a], self.session.songs[s_b]

        self.panel_a["btn"].setText(s_a)
        self.panel_a["lbl"].setText(f"{d_a['album']} ({d_a['year']})")
        self.load_cover(d_a.get("cover_url"), self.panel_a["cover"])

        self.panel_b["btn"].setText(s_b)
        self.panel_b["lbl"].setText(f"{d_b['album']} ({d_b['year']})")
        self.load_cover(d_b.get("cover_url"), self.panel_b["cover"])

        self.web_view.setHtml(
            '<h1 style="color:white;text-align:center;font-family:sans-serif;margin-top:20%;">Preview</h1>'
        )
        self.stop_audio()

    def vote(self, side):
        if not self.current_pair:
            return
        win, los = (
            (self.current_pair[0], self.current_pair[1])
            if side == "A"
            else (self.current_pair[1], self.current_pair[0])
        )
        self.session.update_score(win, los)
        self.update_status("Rated.")
        self.next_matchup()

    def skip_matchup(self):
        """Skip current matchup without updating scores."""
        if not self.current_pair:
            return
        self.update_status("Skipped.")
        self.next_matchup()

    def play_video(self, side):
        if not self.current_pair:
            return
        s = self.current_pair[0] if side == "A" else self.current_pair[1]
        d = self.session.songs[s]
        self.update_status(f"Searching video for {s}...")
        self.y_worker = Worker(
            "find_video", {"artist": d["artist"], "title": s, "album": d["album"]}
        )
        self.y_worker.finished.connect(lambda url: self.on_video_found(url))
        self.y_worker.start()

    def on_video_found(self, url):
        if url:
            self.web_view.setUrl(QUrl(url))
        else:
            self.update_status("Video not found.")

    def play_audio_preview(self, side):
        # If already playing this side, simplify toggle to STOP
        if (
            hasattr(self, "active_audio_side")
            and self.active_audio_side == side
            and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.stop_audio()
            return

        # Logic to find song
        if not self.current_pair:
            return

        idx = 0 if side == "A" else 1
        s = self.current_pair[idx]

        d = self.session.songs.get(s)
        if not d:
            return

        # Update UI to Loading
        panel = self.panel_a if side == "A" else self.panel_b
        panel["audio_btn"].setText("⏳ Loading...")

        # Check if we already have the URL
        if "preview_url" in d and d["preview_url"]:
            print(f"DEBUG: Preview URL found in cache for {s}: {d['preview_url']}")
            self.update_status(f"Playing preview for {s}...")
            self.play_audio_url(d["preview_url"], side)
            return

        # Check if we already looked and failed (empty string)
        if "preview_url" in d and d["preview_url"] == "":
            print(f"DEBUG: Preview URL was previously found to be empty for {s}")
            self.update_status("No preview available.")
            panel["audio_btn"].setText("✖ Not Found")
            # Revert text after a delay?
            QTimer.singleShot(
                2000, lambda: panel["audio_btn"].setText("♫ Audio Preview")
            )
            return

        print(
            f"DEBUG: Searching preview for {s} (Artist: {d['artist']}, Album: {d['album']})..."
        )
        self.update_status(f"Searching preview for {s}...")
        self.a_worker = Worker(
            "find_audio", {"artist": d["artist"], "title": s, "album": d["album"]}
        )
        # Capturing 's' in default arg to avoid late binding issue if multiple calls?
        # actually lambda inside connect or functools.partial is safer
        # self.a_worker.finished.connect(lambda url: self.on_audio_found(url, s))
        # But 's' changes? No wait.
        # We need to know which song this was for.
        self.a_worker.finished.connect(
            lambda url, song=s: self.on_audio_found(url, song)
        )
        self.a_worker.start()

    def on_audio_found(self, url, song_title):
        print(f"DEBUG: on_audio_found called for {song_title}. URL: '{url}'")
        if song_title not in self.session.songs:
            print("DEBUG: Song no longer in session.")
            return  # Song deleted or something?

        if url:
            self.session.songs[song_title]["preview_url"] = url
            self.session.has_unsaved_changes = True

            # If still on the same match and user wants to play it?
            # We assume user still wants to hear it.
            self.update_status(f"Preview found for {song_title}.")
            # Pass side info if we knew it?
            # Actually play_audio_url needs to find the right panel to update UI
            # Let's verify which side this song belongs to
            side = None
            if self.current_pair:
                if self.current_pair[0] == song_title:
                    side = "A"
                elif self.current_pair[1] == song_title:
                    side = "B"

            self.play_audio_url(url, side)
        else:
            self.session.songs[song_title]["preview_url"] = ""  # Mark as not found
            self.update_status("Preview not found.")

            # Find which panel has this song currently
            target_panel = None
            if self.current_pair:
                if self.current_pair[0] == song_title:
                    target_panel = self.panel_a
                elif self.current_pair[1] == song_title:
                    target_panel = self.panel_b

            if target_panel:
                target_panel["audio_btn"].setText("✖ Not Found")
                # Revert text after a delay
                QTimer.singleShot(
                    2000, lambda: target_panel["audio_btn"].setText("♫ Audio Preview")
                )

    def play_audio_url(self, url, side=None):
        print(f"DEBUG: play_audio_url called with: {url}")

        # Stop any existing
        self.stop_audio()

        # Update UI for Playing state if side is known
        self.active_audio_side = side
        if side:
            panel = self.panel_a if side == "A" else self.panel_b
            panel["audio_btn"].setText("⏹ Stop Preview")
            panel["prog"].setVisible(True)
            panel["prog"].setValue(0)

        try:
            self.player.setSource(QUrl(url))
            self.player.play()
            print("DEBUG: QMediaPlayer playing...")
        except Exception as e:
            print(f"DEBUG: QMediaPlayer Error: {e}")

    def stop_audio(self):
        try:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.stop()
        except Exception:
            pass

        self.reset_audio_ui()

    def reset_audio_ui(self):
        # Helper to reset buttons to default state
        for p in [self.panel_a, self.panel_b]:
            if "audio_btn" in p:
                p["audio_btn"].setText("♫ Audio Preview")
            if "prog" in p:
                p["prog"].setVisible(False)
                p["prog"].setValue(0)
        self.active_audio_side = None

    def on_audio_position_changed(self, position):
        if hasattr(self, "active_audio_side") and self.active_audio_side:
            panel = self.panel_a if self.active_audio_side == "A" else self.panel_b
            # Duration is usually 30000ms (30s)
            # But let's use the actual duration if available
            duration = self.player.duration()
            if duration > 0:
                panel["prog"].setMaximum(duration)
                panel["prog"].setValue(position)

    def on_audio_duration_changed(self, duration):
        if hasattr(self, "active_audio_side") and self.active_audio_side:
            panel = self.panel_a if self.active_audio_side == "A" else self.panel_b
            panel["prog"].setMaximum(duration)

    def on_audio_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop_audio()

    def load_cover(self, url, label_widget):
        label_widget.clear()
        label_widget.setText("Loading...")
        if not url:
            label_widget.setText("No Cover")
            return

        # Check Memory Cache
        if url in self.image_cache:
            label_widget.setPixmap(self.image_cache[url])
            return

        req = QNetworkRequest(QUrl(url))
        # Ensure disk cache is used
        req.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.PreferCache,
        )

        reply = self.network_manager.get(req)
        self.active_downloads[reply] = label_widget

    def on_image_downloaded(self, reply):
        label_widget = self.active_downloads.pop(reply, None)
        if not label_widget:
            reply.deleteLater()
            return

        url = reply.request().url().toString()

        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pix = QPixmap()
            pix.loadFromData(data)

            if not pix.isNull():
                # Cache in memory only if valid
                self.image_cache[url] = pix
                label_widget.setPixmap(pix)
            else:
                label_widget.setText("Invalid Image")
        else:
            label_widget.setText("Failed")
        reply.deleteLater()

    def show_leaderboard(self):
        self.win_t = QWidget()
        self.win_t.setWindowTitle(f"Leaderboard: {self.session.active_filter}")
        self.win_t.resize(700, 600)
        l = QVBoxLayout(self.win_t)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["Rank", "Artist", "Song", "Score"])
        self.table_widget.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        # Enable extended selection (Shift/Ctrl click) for multiple rows
        self.table_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table_widget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        l.addWidget(self.table_widget)

        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.win_t.close)

        btn_delete = QPushButton("🗑 Delete Selected")
        btn_delete.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold;"
        )

        btn_add = QPushButton("➕ Add Song")
        btn_add.clicked.connect(lambda: add_manual_song())
        btn_add.setStyleSheet(
            "background-color: #2ecc71; color: white; font-weight: bold;"
        )

        btn_merge = QPushButton("🔗 Merge Selected")
        btn_merge.clicked.connect(lambda: merge_selected_songs())
        btn_merge.setStyleSheet(
            "background-color: #f39c12; color: white; font-weight: bold;"
        )

        btn_export = QPushButton("Export Playlist (CSV)")
        btn_export.clicked.connect(lambda: export_csv())
        btn_export.setStyleSheet(
            "background-color: #1DB954; color: white; font-weight: bold;"
        )

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_merge)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        l.addLayout(btn_layout)

        def export_csv():
            keys = self.session.get_filtered_keys()
            sorted_keys = sorted(
                keys, key=lambda k: self.session.songs[k]["score"], reverse=True
            )

            if not sorted_keys:
                QMessageBox.warning(self.win_t, "Export", "No songs to export!")
                return

            fname, _ = QFileDialog.getSaveFileName(
                self.win_t, "Export CSV", "", "CSV Files (*.csv)"
            )
            if not fname:
                return

            try:
                import csv

                with open(fname, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # Header compliant with most importers
                    writer.writerow(
                        ["Title", "Artist", "Album", "Year", "Rank", "Score"]
                    )

                    for i, key in enumerate(sorted_keys):
                        d = self.session.songs[key]
                        writer.writerow(
                            [
                                key,
                                d.get("artist", ""),
                                d.get("album", ""),
                                d.get("year", ""),
                                i + 1,
                                int(d["score"]),
                            ]
                        )

                QMessageBox.information(
                    self.win_t,
                    "Export Successful",
                    f"Exported {len(sorted_keys)} songs to:\n{fname}\n\nYou can import this CSV into Spotify using tools like Soundiiz or TuneMyMusic.",
                )
            except Exception as e:
                QMessageBox.critical(self.win_t, "Export Failed", str(e))

        def populate_table():
            # Only show songs from current filter
            keys = self.session.get_filtered_keys()
            # Sort them
            sorted_keys = sorted(
                keys, key=lambda k: self.session.songs[k]["score"], reverse=True
            )

            self.table_widget.setRowCount(len(sorted_keys))
            for i, key in enumerate(sorted_keys):
                d = self.session.songs[key]
                # Rank
                item_rank = QTableWidgetItem(str(i + 1))
                item_rank.setFlags(item_rank.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table_widget.setItem(i, 0, item_rank)

                # Artist
                item_artist = QTableWidgetItem(d["artist"])
                item_artist.setFlags(item_artist.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table_widget.setItem(i, 1, item_artist)

                # Song
                item_song = QTableWidgetItem(key)
                item_song.setFlags(item_song.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table_widget.setItem(i, 2, item_song)

                # Score
                item_score = QTableWidgetItem(str(int(d["score"])))
                item_score.setFlags(item_score.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table_widget.setItem(i, 3, item_score)

        def delete_selected():
            selected_rows = sorted(
                set(index.row() for index in self.table_widget.selectedIndexes()),
                reverse=True,
            )
            if not selected_rows:
                return

            # Confirm deletion? (Optional, but good practice. For now just do it as requested "just deleting rows")

            for row in selected_rows:
                song_item = self.table_widget.item(row, 2)
                if song_item:
                    song_key = song_item.text()
                    if song_key in self.session.songs:
                        del self.session.songs[song_key]
                        self.session.has_unsaved_changes = True

            self.update_status(f"Deleted {len(selected_rows)} songs.")
            populate_table()

            # Refresh matchup if current pair was deleted
            if self.current_pair:
                s_a, s_b = self.current_pair
                if s_a not in self.session.songs or s_b not in self.session.songs:
                    self.next_matchup()

        def add_manual_song():
            # Find common artist to pre-fill
            common_artist = ""
            keys = self.session.get_filtered_keys()
            if keys:
                # Just take the artist of the first song in filter for simplicity
                common_artist = self.session.songs[keys[0]]["artist"]

            # Get existing albums for autocomplete
            existing_albums = self.session.get_albums_list()

            dlg = AddSongDialog(self.win_t, common_artist, existing_albums)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                title = data["title"]
                if not title:
                    QMessageBox.warning(self.win_t, "Error", "Title is required.")
                    return

                if title in self.session.songs:
                    QMessageBox.warning(self.win_t, "Error", "Song already exists!")
                    return

                # Add to session
                self.session.songs[title] = {
                    "artist": data["artist"] if data["artist"] else "Unknown Artist",
                    "album": data["album"] if data["album"] else "Unknown Album",
                    "year": data["year"] if data["year"] else "????",
                    "score": 1200,
                    "matches": 0,
                    "cover_url": None,
                }
                self.session.has_unsaved_changes = True
                self.update_status(f"Added manual song: {title}")
                self.refresh_filter_list()  # Update filter dropdown in main window in case new album added
                populate_table()

        def merge_selected_songs():
            selected_rows = sorted(
                set(index.row() for index in self.table_widget.selectedIndexes())
            )
            if len(selected_rows) < 2:
                QMessageBox.warning(
                    self.win_t, "Merge", "Select at least 2 songs to merge."
                )
                return

            # Get song keys
            keys_to_merge = []
            for row in selected_rows:
                item = self.table_widget.item(row, 2)
                if item:
                    keys_to_merge.append(item.text())

            if not keys_to_merge:
                return

            # Propose new title (default to first one)
            first_key = keys_to_merge[0]
            new_title, ok = QInputDialog.getText(
                self.win_t, "Merge Songs", "New Title for Merged Song:", text=first_key
            )
            if not ok or not new_title:
                return

            new_title = new_title.strip()

            # Check if target exists (and is not one of the merged ones)
            if new_title in self.session.songs and new_title not in keys_to_merge:
                QMessageBox.warning(
                    self.win_t, "Error", "Target song title already exists!"
                )
                return

            # Calculate stats
            total_matches = 0
            score_sum = 0

            # Use metadata from first song
            first_data = self.session.songs[first_key]
            artist = first_data["artist"]
            album = first_data["album"]
            year = first_data["year"]
            cover_url = first_data.get("cover_url")

            for k in keys_to_merge:
                d = self.session.songs[k]
                total_matches += d["matches"]
                score_sum += d["score"]

            avg_score = score_sum / len(keys_to_merge)

            # Create new entry
            self.session.songs[new_title] = {
                "artist": artist,
                "album": album,
                "year": year,
                "score": avg_score,
                "matches": total_matches,
                "cover_url": cover_url,
            }

            # Delete old entries
            # If new title is same as one of old keys, define it first (above) then delete others?
            # Actually we overwrote/set new_title above.
            # Now we must delete the OLD keys.
            # CAREFUL: If new_title is one of the keys_to_merge, we just overwrote it. We shouldn't delete it.

            for k in keys_to_merge:
                if k != new_title:
                    if k in self.session.songs:
                        del self.session.songs[k]

            self.session.has_unsaved_changes = True
            self.update_status(f"Merged {len(keys_to_merge)} songs into '{new_title}'.")
            populate_table()

            # Refresh matchup if current pair was affected
            if self.current_pair:
                s_a, s_b = self.current_pair
                if s_a not in self.session.songs or s_b not in self.session.songs:
                    self.next_matchup()

        btn_delete.clicked.connect(delete_selected)
        populate_table()
        self.win_t.show()

    def show_album_leaderboard(self):
        self.win_alb = QWidget()
        self.win_alb.setWindowTitle("Album Rankings")
        self.win_alb.resize(800, 600)
        l = QVBoxLayout(self.win_alb)

        self.album_table = QTableWidget()
        self.album_table.setColumnCount(5)
        self.album_table.setHorizontalHeaderLabels(
            ["Rank", "Cover", "Album", "Avg Score", "Songs"]
        )
        self.album_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.album_table.verticalHeader().setDefaultSectionSize(70)  # Space for covers
        self.album_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.album_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        l.addWidget(self.album_table)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.win_alb.close)
        l.addWidget(btn_close)

        # Logic to populate
        stats = {}  # album -> {title, total_score, count, cover_url}

        for d in self.session.songs.values():
            alb = d.get("album", "Unknown Album")
            if alb not in stats:
                stats[alb] = {
                    "name": alb,
                    "total": 0,
                    "count": 0,
                    "cover_url": d.get("cover_url"),
                    "artist": d.get("artist", ""),
                }

            stats[alb]["total"] += d["score"]
            stats[alb]["count"] += 1
            if not stats[alb]["cover_url"] and d.get("cover_url"):
                stats[alb]["cover_url"] = d.get("cover_url")

        # Convert to list
        album_list = []
        for v in stats.values():
            avg = v["total"] / v["count"] if v["count"] > 0 else 0
            v["avg"] = avg
            album_list.append(v)

        # Sort by Avg Score Descending
        album_list.sort(key=lambda x: x["avg"], reverse=True)

        self.album_table.setRowCount(len(album_list))

        for i, item in enumerate(album_list):
            # Rank
            self.album_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # Cover Widget
            lbl_cover = QLabel()
            lbl_cover.setFixedSize(60, 60)
            lbl_cover.setScaledContents(True)
            lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_cover.setStyleSheet("background-color: #333; border: 1px solid #444;")

            self.album_table.setCellWidget(i, 1, lbl_cover)

            if item["cover_url"]:
                self.load_cover(item["cover_url"], lbl_cover)
            else:
                lbl_cover.setText("No Img")

            # Album Name + Artist
            text_str = f"{item['name']}\n{item['artist']}"
            self.album_table.setItem(i, 2, QTableWidgetItem(text_str))

            # Avg Score
            self.album_table.setItem(i, 3, QTableWidgetItem(f"{item['avg']:.1f}"))

            # Count
            self.album_table.setItem(i, 4, QTableWidgetItem(str(item["count"])))

        self.win_alb.show()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        # Worker mode for fetching data in subprocess
        import fetch_data

        # Remove '--worker' from args so fetch_data sees expected structure
        sys.argv.pop(1)
        fetch_data.main()
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark Mode Palette
    from PyQt6.QtGui import QPalette, QColor

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(224, 224, 224))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(224, 224, 224))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(224, 224, 224))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(
        QPalette.ColorRole.Link, QColor(230, 126, 34)
    )  # Orange accent
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(230, 126, 34))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(dark_palette)

    # Global Stylesheet for generic widgets
    app.setStyleSheet(
        """
        QToolTip { 
            color: #ffffff; 
            background-color: #2a2a2a; 
            border: 1px solid white; 
        }
        QMainWindow, QDialog {
            background-color: #121212;
        }
        
    """
    )

    # Fix YouTube Error 153: Mimic a standard Chrome browser
    # Using a specific recent version helps avoid "bot" detection
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36"
    QWebEngineProfile.defaultProfile().setHttpUserAgent(user_agent)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
