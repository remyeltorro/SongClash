# The Android app

SongClash runs on Android as a [Toga](https://toga.readthedocs.io) app, packaged
with [Briefcase](https://briefcase.readthedocs.io). It shares `core/` and
`services/` with the desktop app. Only the UI (`src/songclash/mobile/`) is
different.

## Building the APK (Windows)

Double-click `build_android.bat`. It:

1. creates `.venv-mobile` and installs Briefcase and Toga,
2. generates the launcher icons (`python scripts/make_icon.py --android`),
3. runs `briefcase build android` and `briefcase package android -p debug-apk`,
4. copies the result to `dist\SongClash.apk`.

The first build downloads the Android SDK (and a JDK if `JAVA_HOME` isn't a
JDK 17) into Briefcase's cache. That's a few GB and takes a while. Later
builds take a minute or two.

The APK is signed with a debug key: it installs on any phone but can't go on
the Play Store. That's all you need for a personal app.

## Installing on a phone

**Without a cable.** Copy `dist\SongClash.apk` to the phone (Google Drive,
e-mail, USB file transfer...) and open it. Android asks you to allow
installing apps from that source (Settings → Apps → Special app access →
Install unknown apps) the first time.

**With USB debugging** (Settings → About phone → tap *Build number* 7 times,
then Developer options → USB debugging):

```bat
adb install -r dist\SongClash.apk
```

`-r` keeps your sessions when you update the app. Uninstalling the app deletes
them, so export anything you want to keep first.

## Using the app

| Screen | What it does |
| --- | --- |
| **Battle** | Tap a song's title card to vote for it. **Undo** reverts the last vote, **Skip** picks another pair. **Play** streams a 30 s iTunes preview. The weight class picker ranks within one album. |
| **Songs** | The leaderboard for the current album filter, podium in gold, silver and bronze. Tap a song to merge it with another or delete it. **Export CSV** saves a playlist you can import into Spotify with Soundiiz or TuneMyMusic. |
| **Albums** | Albums ranked by the average score of their songs. Tap one to battle only its songs or delete it. |
| **Artist** | Search MusicBrainz, pick the artist and release types, and import. |
| **Sessions** | Rename, start, open or delete sessions. **Export** / **Import a Session File** exchange `.json` session files with the desktop app. |

Sessions are saved automatically after every change, in the app's private
storage. The app reopens the last session on launch.

## Development

Preview the mobile UI on the desktop (no audio, no rounded corners, Windows dialogs):

```bash
pip install -e ".[mobile]"
python -m songclash.mobile
```

Run it in the Android emulator (Briefcase offers to create one):

```bash
briefcase run android
```

How the pieces fit:

| Module | Role |
| --- | --- |
| `mobile/app.py` | `SongClashMobile` (a `toga.App`): owns the session, saves it, and switches screens |
| `mobile/battle.py`, `rankings.py`, `importer.py`, `sessions.py` | screens: build widgets, call back into the app |
| `mobile/library.py` | session files and settings in the app's data folder (plain Python, tested) |
| `mobile/audio.py` | preview lookup and play/stop state |
| `mobile/covers.py` | cover downloads, cached in memory and on disk |
| `mobile/device.py` | Android APIs through Chaquopy (MediaPlayer, file pickers, toasts, rounded/gradient backgrounds), with desktop fallbacks |
| `mobile/theme.py` | the desktop's colors, plus pills, cards and badges built from Pack styles and native drawables |

`python -m songclash` starts the Toga app on Android and the PyQt6 app
everywhere else. Briefcase reads its settings from `[tool.briefcase]` in
`pyproject.toml`. Because Briefcase bundles `[project].dependencies` into
the APK, desktop-only packages (PyQt6) live in the `desktop` extra.
