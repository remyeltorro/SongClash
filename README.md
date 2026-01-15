<p align="center">
  <img src="app_icon.png" alt="Ultimate Song Ranker Logo" width="150">
</p>

# Ultimate Song Ranker (RankSongs)

**Ultimate Song Ranker** is a desktop application designed to help music fans definitely rank their favorite artist's discography. Instead of subjectively listing songs, you participate in a series of head-to-head "battles" between two songs. The app uses an **ELO rating system** (similar to chess rankings) to calculate a precise leaderboard based on your choices.

## Features

-   **🎵 Automated Discography Import**: Fetches complete artist discographies from **MusicBrainz**, ensuring accurate metadata.
-   **🧠 Smart Matchmaking**:
    -   **Fair Fights**: Prioritizes matchups between songs with similar skill levels (ELO scores) to make decisions tougher and accurate.
    -   **Coverage**: Prioritizes songs with fewer matches to ensure every track is ranked.
-   **🚫 Intelligent Filtering**: Automatically filters out Live albums, Bootlegs, Compilations, and non-studio tracks (customizable).
-   **📽️ Multimedia Previews**:
    -   **Audio**: Fetches 30-second previews from iTunes.
    -   **Video**: integrated YouTube search fallback for song playback.
    -   **Art**: Displays high-quality album art.
-   **💾 Session Management**: Save your progress to JSON, load previous sessions, or **Merge** multiple sessions together.
-   **🌑 Modern Dark UI**: A polished, dark-themed interface built with PyQt6.
-   **📊 Dynamic Leaderboard**: Watch the rankings update in real-time as you vote.

## Installation

**The easiest way to use Ultimate Song Ranker is to download the latest release.**

1.  Go to the [Releases](../../releases) page on GitHub.
2.  Download the latest `UltimateSongRanker.exe`.
3.  Run the executable directly (no installation required).

### Running from Source (Advanced)

If you prefer to run the application from Python source code:

1.  Ensure you have **Python 3.10+** and **PIP** installed.
2.  Clone the repository and install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Simply double-click `UltimateSongRanker.exe` to launch the app.

If running from source:
```bash
python __main__.py
```

### How to Rank
1.  **Start a Session**:
    -   Go to **File > New Session**.
    -   **Add Music > Add Artist from Web...**: Type an artist name (e.g., "The Beatles").
    -   *Optional*: Adjust the filter settings (uncheck "Live" or "Bootleg" if you only want studio albums).
2.  **Battle!**:
    -   You will be presented with two songs. Click on the one you prefer.
    -   The "win" is recorded, and the ELO scores are updated.
    -   Continue battling to refine the leaderboard.
3.  **View Results**:
    -   Switch to the **Rankings** tab to see the sorted list of songs with their scores and win/loss records.
4.  **Save**:
    -   **File > Save** to store your ranking session (`.json`) and resume later.

## Under the Hood

### ELO Rating System
The app uses a standard **ELO rating formula** with a K-factor of 32.
-   **Initial Score**: All songs start at 1200.
-   **Updates**: When Song A beats Song B, A gains points and B loses points. The amount depends on their current rating difference (upsets cause larger score swings).

### Data Fetching
-   **MusicBrainz**: Used as the source of truth for Artist, Album, and Track data. The app performs strict normalization to deduplicate tracks (e.g., "Remaster 2009" vs "Original").
-   **Concurrency**: Networking tasks (API calls, image downloading) are handled in background threads (`QThread` and `Subprocess`) to keep the UI responsive.

## Building (Optional)
To create a standalone Windows `.exe`:
1.  Run the included build script:
    ```cmd
    build.bat
    ```
2.  The executable will be located in the `dist/` folder.
