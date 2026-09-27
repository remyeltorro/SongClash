"""The mobile app: owns the RankingSession and switches between screens.

Screens display state and call back into ``SongClashMobile``, which changes
the session, saves it, and refreshes what's on screen (the same split as the
desktop MainWindow).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import toga
from toga.style import Pack
from toga.style.pack import BOLD, COLUMN, NONE, PACK

from songclash import APP_NAME, __version__
from songclash.core import storage
from songclash.core.session import RankingSession
from songclash.mobile import device, theme
from songclash.mobile.audio import PreviewController
from songclash.mobile.battle import BattleScreen
from songclash.mobile.covers import CoverCache
from songclash.mobile.importer import ImportScreen
from songclash.mobile.library import SessionLibrary, safe_name
from songclash.mobile.rankings import AlbumsScreen, SongsScreen
from songclash.mobile.sessions import SessionsScreen

log = logging.getLogger(__name__)

APP_ID = "io.github.remyeltorro.songclash"
NAV = [  # bottom tab bar: (page, icon, label)
    ("battle", "⚔", "Battle"),
    ("songs", "♛", "Songs"),
    ("albums", "◉", "Albums"),
    ("import", "＋", "Artist"),
    ("sessions", "☰", "Sessions"),
]
MESSAGE_SECONDS = 5


class SongClashMobile(toga.App):
    def startup(self):
        self.library = SessionLibrary(self.paths.data)
        self.covers = CoverCache(self.paths.cache)
        self.session = RankingSession()
        self.current_pair: list[str] | None = None
        self.current_page = None
        self._message_token = 0

        self.audio = PreviewController(self._on_audio_state, self.message)
        self.pages = {
            "battle": BattleScreen(self),
            "songs": SongsScreen(self),
            "albums": AlbumsScreen(self),
            "import": ImportScreen(self),
            "sessions": SessionsScreen(self),
        }

        self.nav = {
            name: theme.pill(
                f"{icon}\n{label}",
                lambda w, name=name, **kw: self.show(name),
                "tab",
                56,
                radius=14,
                size=12,
                flex=1,
            )
            for name, icon, label in NAV
        }
        self.holder = toga.Box(style=Pack(direction=COLUMN, flex=1, background_color=theme.BG))
        # Messages show as Android toasts; elsewhere in this label
        self.status = toga.Label(
            "", style=theme.text(13, theme.GOLD, margin=(4, 14), display=NONE, font_weight=BOLD)
        )
        tab_bar = toga.Box(
            children=list(self.nav.values()),
            style=theme.row(flex=1, gap=4, margin=(6, 8), background_color=theme.BG_DEEP),
        )
        root = toga.Box(
            children=[
                self.holder,
                self.status,
                toga.Box(children=[tab_bar], style=Pack(background_color=theme.BG_DEEP)),
            ],
            style=Pack(direction=COLUMN, flex=1, background_color=theme.BG),
        )

        self.main_window = toga.MainWindow(title=APP_NAME)
        self.main_window.content = root
        device.style_window(self, theme.BG_DEEP)

        last = self.library.last_session()
        if last:
            self.open_session(last, announce=False)
        else:
            self.show("battle")
        self.main_window.show()

    # ==========================
    # NAVIGATION & FEEDBACK
    # ==========================
    def show(self, name):
        self.show_screen(self.pages[name])
        for key, btn in self.nav.items():
            theme.restyle(btn, "tab_active" if key == name else "tab")

    def show_screen(self, screen):
        if screen is not self.pages["battle"]:
            self.audio.stop()
        self.current_page = screen
        screen.refresh()
        self.holder.clear()
        self.holder.add(screen.box)

    def message(self, text):
        if device.toast(self, text):
            return
        self._message_token += 1
        token = self._message_token
        self.status.text = theme.wrap(text, size=13)
        self.status.style.display = PACK

        async def clear():
            await asyncio.sleep(MESSAGE_SECONDS)
            if self._message_token == token:
                self.status.style.display = NONE

        asyncio.ensure_future(clear())

    async def info(self, title, text):
        await self.main_window.dialog(toga.InfoDialog(title, text))

    async def confirm(self, title, text) -> bool:
        return await self.main_window.dialog(toga.ConfirmDialog(title, text))

    def refresh_title(self):
        if not device.style_window(self, theme.BG_DEEP, subtitle=self.session_name()):
            self.main_window.title = f"{APP_NAME} · {self.session_name()}"

    # ==========================
    # PERSISTENCE (automatic)
    # ==========================
    def session_name(self):
        return Path(self.session.current_filename).stem if self.session.current_filename else "Untitled"

    def save(self, name=None):
        """Save the session, creating its file (called ``name``) if needed."""
        s = self.session
        if not s.songs and not s.current_filename:
            return
        try:
            s.save_session(s.current_filename or str(self.library.new_path(name or "Session")))
        except OSError as e:
            self.message(f"Could not save: {e}")
            return
        self.library.set_last_session(s.current_filename)
        self.refresh_title()

    def open_session(self, path, announce=True):
        self.audio.stop()
        try:
            count = self.session.load_from_file(str(path))
        except (OSError, ValueError) as e:
            self.session.new_session()
            self.library.set_last_session(None)
            self.message(f"Could not open {Path(path).name}: {e}")
            count = None
        else:
            self.library.set_last_session(path)
        self.audio.forget_misses()
        self.refresh_title()
        self.next_matchup()
        self.show("battle")
        if announce and count is not None:
            self.message(f"Loaded {count} songs.")

    def new_session(self):
        self.audio.stop()
        self.session.new_session()
        self.library.set_last_session(None)
        self.refresh_title()
        self.next_matchup()
        self.show("battle")
        self.message("New session. Add an artist to start.")

    def delete_session(self, path):
        if self.session.current_filename and Path(path) == Path(self.session.current_filename):
            self.session.new_session()
            self.library.set_last_session(None)
            self.refresh_title()
            self.next_matchup()
        self.library.delete(path)
        self.show("sessions")

    def rename_session(self, name):
        name = name.strip()
        if not name:
            return
        s = self.session
        if s.current_filename:
            try:
                s.current_filename = str(self.library.rename(s.current_filename, name))
            except OSError as e:
                self.message(f"Could not rename: {e}")
                return
            self.library.set_last_session(s.current_filename)
        elif s.songs:
            self.save(name)
        else:
            self.message("Add songs before naming the session.")
            return
        self.refresh_title()
        self.show("sessions")
        self.message(f"Renamed to '{self.session_name()}'.")

    async def save_document(self, title, filename, mime, content: bytes):
        try:
            return await device.save_document(self, title, filename, mime, content)
        except Exception as e:  # anything from the Android storage framework
            log.exception("Export failed")
            await self.info("Export Failed", str(e))
            return None

    async def export_session(self):
        if not self.session.songs:
            await self.info("Export", "This session has no songs yet.")
            return
        content = storage.dumps_session(self.session.songs).encode("utf-8")
        saved = await self.save_document(
            "Export Session", f"{safe_name(self.session_name())}.json", "application/json", content
        )
        if saved:
            self.message(f"Exported to {saved}.")

    async def import_session_file(self):
        try:
            picked = await device.open_document(self, "Import Session", "json")
            if picked is None:
                return
            filename, content = picked
            songs = storage.loads_session(content)
        except Exception as e:  # unreadable file, not a session, storage errors
            await self.info("Import Failed", f"That file isn't a SongClash session.\n\n{e}")
            return

        if self.session.songs and await self.main_window.dialog(
            toga.QuestionDialog(
                "Import Session",
                f"Merge the {len(songs)} songs into '{self.session_name()}'?\n\n"
                "Choose No to open the file as a separate session.",
            )
        ):
            added = self.session.merge_songs(songs)
            self.songs_changed(f"Merged {added} new songs.", screen="battle")
            return
        path = self.library.new_path(Path(filename).stem)
        try:
            storage.write_session(path, songs)
        except OSError as e:
            await self.info("Import Failed", str(e))
            return
        self.open_session(path)

    # ==========================
    # CHANGES
    # ==========================
    def songs_changed(self, text, screen=None):
        """Songs were added, removed or merged: save and redraw."""
        pair_gone = not self.current_pair or any(k not in self.session.songs for k in self.current_pair)
        self.save()
        if pair_gone:
            self.next_matchup()
        if screen:
            self.show(screen)
        elif self.current_page:
            self.current_page.refresh()
        self.message(text)

    async def artist_imported(self, name, songs):
        if not songs:
            await self.info("Add Artist", f"No songs found for {name} with the selected release types.")
            return
        added = self.session.add_fetched_songs(songs)
        # A brand-new session is named after its first artist
        self.save(name)
        self.songs_changed(
            f"Added {added} songs by {name}." if added else f"All songs by {name} were already here.",
            screen="battle",
        )

    # ==========================
    # BATTLE
    # ==========================
    def set_filter(self, album):
        self.session.active_filter = album
        self.next_matchup()

    def next_matchup(self):
        self.show_pair(self.session.get_matchup())

    def show_pair(self, pair):
        self.audio.stop()
        self.current_pair = pair
        battle = self.pages["battle"]
        battle.show_pair([self.session.songs[k] for k in pair] if pair else None)
        battle.refresh_stats()
        if not pair and self.session.songs:
            self.message("This album has fewer than 2 songs. Pick another one.")

    def vote(self, side):
        if not self.current_pair:
            return
        a, b = self.current_pair
        winner, loser = (a, b) if side == "A" else (b, a)
        self.session.update_score(winner, loser)
        self.save()
        self.next_matchup()

    def skip(self):
        if self.current_pair:
            self.next_matchup()

    def undo(self):
        pair = self.session.undo_last_vote()
        if pair:
            self.save()
            self.show_pair(list(pair))
            self.message("Last vote undone.")

    def toggle_preview(self, side):
        if not self.current_pair:
            return
        key = self.current_pair[0 if side == "A" else 1]
        self.audio.toggle(side, key, self.session.songs.get(key))

    def _on_audio_state(self, side, state):
        self.pages["battle"].set_audio_state(side, state)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return SongClashMobile(formal_name=APP_NAME, app_id=APP_ID, version=__version__)
