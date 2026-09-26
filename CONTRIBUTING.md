# Contributing

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (source .venv/bin/activate elsewhere)
pip install -e ".[dev]"
```

The editable install (`-e`) means code changes apply without reinstalling.

## Everyday commands

```bash
python -m songclash            # run the app
python -m pytest               # run the tests
ruff check . --fix             # lint (and auto-fix what it can)
ruff format .                  # format
python scripts/fetch_artist.py "Radiohead"   # debug the MusicBrainz import
```

CI runs `ruff check`, `ruff format --check` and `pytest` on every push and pull
request (`.github/workflows/ci.yml`).

## Before opening a pull request

- Keep `core/` and `services/` free of Qt imports (see
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- Add or update tests for behavior changes. Bug fixes should come with a
  regression test.
- Tests must not hit the network. Monkeypatch `requests` or the client.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `docs:`, `build:`...).

## Releasing

1. Bump `__version__` in `src/songclash/__init__.py`.
2. Tag and push: `git tag v1.2.0 && git push origin v1.2.0`.
3. `.github/workflows/release.yml` tests, builds `SongClash.exe` from
   `packaging/songclash.spec` and attaches it to a GitHub release.

To build locally, run `build.bat`.
