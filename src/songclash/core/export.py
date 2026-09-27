"""Exporting rankings to other formats."""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Iterable

from songclash.core.models import Song

CSV_HEADER = ["Title", "Artist", "Album", "Year", "Rank", "Score"]


def ranking_csv(ranked: Iterable[Song]) -> str:
    """Songs (best first) as playlist CSV text.

    The format imports into Spotify via Soundiiz or TuneMyMusic.
    """
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(CSV_HEADER)
    for rank, s in enumerate(ranked, start=1):
        writer.writerow([s["title"], s["artist"], s["album"], s["year"], rank, int(round(s["score"]))])
    return out.getvalue()


def write_ranking_csv(path: str | os.PathLike, ranked: Iterable[Song]) -> int:
    """Write songs (best first) as a playlist CSV. Returns the row count.

    The BOM (utf-8-sig) makes Excel detect the encoding.
    """
    ranked = list(ranked)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write(ranking_csv(ranked))
    return len(ranked)
