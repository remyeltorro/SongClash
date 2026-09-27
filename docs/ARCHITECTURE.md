# Architecture

SongClash has two front ends over the same two lower layers. Dependencies
only point downwards:

```
ui/        PyQt6 desktop app: widgets, windows, and glue to run services off the GUI thread
mobile/    Toga Android app (see ANDROID.md)
  │
  ├──► services/   Remote data (MusicBrainz, iTunes). Plain blocking Python, no Qt
  │
  └──► core/       Songs, Elo, matchmaking, session files. Pure Python, no Qt, no I/O but files
```

`core` and `services` never import Qt or Toga. That keeps them fast to test and
shared by both front ends. Logic both UIs need (captions, import options, CSV
text) belongs there, not in `ui/` or `mobile/`.

## Layout

```
src/songclash/
├── __init__.py          version, app name, app id
├── __main__.py          `python -m songclash` (Toga app on Android, PyQt6 elsewhere)
├── app.py               QApplication bootstrap, theme, crash dialog
├── resources.py         paths to bundled assets
├── assets/              app_icon.png
├── core/
│   ├── models.py        `Song` record (also the JSON shape), song_key, normalize_song
│   ├── elo.py           rating math
│   ├── matchmaking.py   which two songs battle next
│   ├── storage.py       session file read/write (atomic), legacy-format migration
│   ├── export.py        CSV playlist export
│   └── session.py       RankingSession: the in-memory database, votes, undo, edits
├── services/
│   ├── errors.py        FetchCancelled, FetchError
│   ├── titles.py        title normalization ("Song (2009 Remaster)" == "Song")
│   ├── musicbrainz.py   artist search and discography import
│   └── itunes.py        preview URL lookup
└── ui/
    ├── main_window.py   controller: menus, file actions, voting loop
    ├── welcome_page.py  shown when the session is empty
    ├── battle_page.py   BattlePage + BattlePanel (one "corner")
    ├── widgets.py       SongCard, ClickableLabel, VsEmblem (custom painted)
    ├── leaderboard.py   song and album ranking windows
    ├── dialogs.py       import options, artist picker, add song
    ├── importer.py      the multi-step "Add Artist" flow
    ├── audio.py         preview lookup + playback state
    ├── covers.py        async cover downloads with memory/disk cache
    ├── tasks.py         Task/TaskRunner: run blocking calls on a thread
    ├── settings.py      AppSettings: typed wrapper over QSettings
    ├── styling.py       helpers to tag widgets for the stylesheet
    └── theme.py         colors, palette and the Qt stylesheet
└── mobile/              Toga screens for Android (module list in ANDROID.md)
```

## Key flows

**Voting.** `BattlePage` emits `vote_requested(side)` →
`MainWindow.vote` → `RankingSession.update_score` (Elo, undo stack) →
`MainWindow.next_matchup` → `RankingSession.get_matchup` →
`BattlePage.show_pair`.

**Importing an artist.** `ArtistImporter.start` runs
`musicbrainz.search_artists` in a `Task`, asks the user to pick an artist and
release types, runs `musicbrainz.fetch_discography` in a `Task` with
progress/cancel, then emits `imported(name, songs)` →
`MainWindow.on_artist_fetched` → `RankingSession.add_fetched_songs`.

**Background work.** `Task` runs a function on a daemon thread and reports back
through Qt signals, which are delivered on the GUI thread. Service functions
that take long accept `progress` and `cancel` arguments (`Task.with_progress()`).
Cancellation raises `FetchCancelled`, which `Task` swallows.

**Editing from the leaderboard.** `LeaderboardWindow` edits the session directly,
then emits `songs_changed(message)`, and `MainWindow.on_songs_changed` refreshes
everything.

## Conventions

- **Styling** lives only in `theme.py`. Widgets opt in with an objectName or
  dynamic properties (`styling.styled(widget, "cover", side="A")`). After
  changing a property at runtime, call `styling.repolish(widget)`.
- **Session file format**: a JSON object `{song_key: Song}`. When you add a
  field to `Song`, give it a default in `normalize_song` so old files still
  load. Add a test in `tests/core/test_session.py`.
- **Tests** mirror the package (`tests/core`, `tests/services`, `tests/ui`).
  Service tests monkeypatch HTTP calls and never touch the network. UI tests run
  with `QT_QPA_PLATFORM=offscreen`.

## Extending

| To add… | Touch |
| --- | --- |
| A new metadata/preview source | a module in `services/` returning plain dicts; call it from `ui/` via `Task` |
| A different rating system | `core/elo.py` (or a sibling), used by `RankingSession.update_score` |
| A new matchmaking strategy | `core/matchmaking.py` |
| A new export format | `core/export.py` + a button in `ui/leaderboard.py` |
| A new window/page | a module in `ui/`, wired up in `main_window.py` via signals |
