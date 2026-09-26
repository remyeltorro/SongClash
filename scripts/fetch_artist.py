"""Debug helper: print the songs SongClash would import for an artist.

python scripts/fetch_artist.py "Artist Name"
"""

import sys

from songclash.services.musicbrainz import fetch_discography, search_artists


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/fetch_artist.py <artist name>")
    sys.stdout.reconfigure(encoding="utf-8")
    matches = search_artists(sys.argv[1], limit=1)
    if not matches:
        sys.exit("artist not found")
    a = matches[0]
    found = fetch_discography(a["id"], a["name"], progress=lambda m, p: print(f"[{p:>3}] {m}"))
    for s in found:
        print(f"{s['album']:<40} {s['title']}")
    print(f"{len(found)} songs")


if __name__ == "__main__":
    main()
