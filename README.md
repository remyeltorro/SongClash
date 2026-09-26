<p align="center">
  <img src="src/songclash/assets/app_icon.png" alt="SongClash Logo" width="150">
</p>

# SongClash

**SongClash** is a desktop app that helps music fans definitively rank an artist's discography. Instead of agonizing over a list, you settle a series of head-to-head "battles" between two songs. An **Elo rating system** (the one used for chess rankings) turns your choices into a precise leaderboard.

## Features

-   **🎵 Automated discography import**: fetches an artist's albums from **MusicBrainz**. When several artists share a name, you pick the right one.
-   **🧠 Smart matchmaking**:
    -   **Coverage**: songs with fewer matches are picked first, so every track gets rated.
    -   **Fair fights**: opponents with similar ratings are preferred, which makes each vote more informative.
-   **🚫 Release filtering**: studio albums only by default. EPs, live albums, compilations, bootlegs and more can be included per import.
-   **🎧 Audio previews**: 30-second previews from iTunes. Click the **Play Preview** button or the album cover.
-   **⌨️ Keyboard voting**: `←` / `→` to vote, `↓` to skip, `Ctrl+Z` to undo a misclick.
-   **📊 Live leaderboards**: song and album rankings update as you vote. You can add, merge and delete songs there, and export to CSV (importable into Spotify with Soundiiz or TuneMyMusic).
-   **💾 Sessions**: save progress to JSON, reopen recent sessions, or merge several sessions together. You're warned before unsaved rankings are lost.

## Installation

**The easiest way to use SongClash is to download the latest release.**

1.  Go to the [Releases](../../releases) page on GitHub.
2.  Download the latest `SongClash.exe`.
3.  Run it directly (no installation required).

### Running from source

1.  Install **Python 3.10+**.
2.  Double-click `run.bat`. It creates a virtual environment and installs dependencies on first run.

Or manually:

```bash
pip install -e .
python -m songclash
```

## How to Rank

1.  **Add music**: click **Add an Artist** (or `Ctrl+F`), type a name, and choose which release types to include.
2.  **Battle!**: click the song you prefer, or use the arrow keys. Use **Skip** when you can't decide.
3.  **Narrow it down**: use the album dropdown to rank within a single album.
4.  **View results**: open the **Leaderboard** or **Album Rankings**.
5.  **Save**: `Ctrl+S` saves your session so you can resume later.

## Under the Hood

### Elo rating
Standard Elo formula with a K-factor of 32. Every song starts at 1200. Beating a higher-rated song earns more points than beating a lower-rated one.

### Data fetching
-   **MusicBrainz** is the source of truth. SongClash lists the artist's album release groups, then reads the tracklist of each album's earliest release. Alternate versions ("Remastered 2009", "Live", "Demo"...) are merged into one song, credited to its original album.
-   **Cover Art Archive** provides album art (cached on disk). **iTunes Search** provides audio previews.
-   All network work runs on background threads, so the UI stays responsive and imports can be cancelled.

## Development

```bash
pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

The code lives in `src/songclash/`, split into three layers:

| Package | Purpose |
| --- | --- |
| `core/` | Songs, Elo scoring, matchmaking, session files (pure Python, no Qt) |
| `services/` | MusicBrainz and iTunes lookups (no Qt) |
| `ui/` | PyQt6 windows, pages, widgets and theme |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit together, and [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## Building

To create a standalone Windows `.exe`, run `build.bat`. It sets up a virtual environment, generates the icon and runs PyInstaller with `packaging/songclash.spec`. The executable ends up in `dist/`.

Pushing a `v*` tag builds the exe on GitHub Actions and attaches it to a release.
