import sys
import json
import requests
import time
import re
import io
import musicbrainzngs

import socket

# Force UTF-8 for pipes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# Set global timeout for all network operations (30 seconds)
socket.setdefaulttimeout(30.0)


def fetch_data(artist_name, reject_types=None):
    # Configure MusicBrainz
    musicbrainzngs.set_useragent(
        "SongClashApp", "1.0", "https://github.com/remy1/ranksongs"
    )
    # Be conservative with rate limiting to avoid connection errors
    musicbrainzngs.set_rate_limit(limit_or_interval=1.5, new_requests=1)

    # Default reject types if none provided
    if reject_types is None:
        reject_types = {
            "Live",
            "Compilation",
            "Remix",
            "Soundtrack",
            "Spokenword",
            "Interview",
            "Audio drama",
            "Demo",
            "Audiobook",
            "Bootleg",  # Default to rejecting bootlegs
        }
    else:
        # Ensure it's a set
        reject_types = set(reject_types)

    def run_with_retries(func, *args, **kwargs):
        max_retries = 8
        base_wait = 2.0
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check for connection errors specifically if possible, but generic catch for now is safer for these transient issues
                if (
                    "10054" in str(e)
                    or "Connection aborted" in str(e)
                    or "timeout" in str(e).lower()
                    or isinstance(e, socket.timeout)
                ):
                    wait_time = base_wait * (2**attempt)
                    print(
                        f"STATUS: Network error (timeout/reset): {e}. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    # Add extra delay after retry to give server time to recover
                    time.sleep(0.5)
                else:
                    raise e
        raise Exception(f"Failed after {max_retries} retries")

    print(f"STATUS: Searching {artist_name}...")
    try:
        data = run_with_retries(
            musicbrainzngs.search_artists, artist=artist_name, limit=1
        )
    except Exception as e:
        print(f"STATUS: Artist search failed: {e}")
        return {}

    if not data or not data.get("artist-list"):
        return {}

    artist_data = data["artist-list"][0]
    artist_id = artist_data["id"]
    real_name = artist_data["name"]

    new_songs = {}

    # Pre-compile regex patterns for normalization
    keywords = [
        "remaster",
        "mix",
        "version",
        "live",
        "demo",
        "edit",
        "mono",
        "stereo",
        "remix",
        "deluxe",
        "expanded",
    ]
    # Regex to remove parenthetical content containing keywords
    pattern_str = r"[\(\[][^\)\]]*?(?:" + "|".join(keywords) + r")[^\)\]]*?[\)\]]"
    pattern_re = re.compile(pattern_str, re.IGNORECASE)

    # Regex to remove suffix content starting with " - " containing keywords
    suffix_pattern_str = r"\s-\s.*?(?:" + "|".join(keywords) + r").*?$"
    suffix_pattern_re = re.compile(suffix_pattern_str, re.IGNORECASE)

    # Helper for normalization
    def normalize_title(title):
        n = title.lower()
        n = n.replace("’", "'").replace("‘", "'").replace("`", "'")
        n = n.replace("“", '"').replace("”", '"')
        n = pattern_re.sub("", n)
        n = suffix_pattern_re.sub("", n)
        return n.strip()

    # Track normalized titles to original titles for O(1) lookup
    # Format: { normalized_title: original_title }
    normalized_lookup = {}

    print(f"STATUS: Fetching release data for {real_name}...")

    limit = 30
    offset = 0
    total_processed = 0

    while True:
        try:
            # We filter for 'album' type on the server side to reduce payload
            # AND include recordings (tracks) and release-group (for type filtering)
            resp = run_with_retries(
                musicbrainzngs.browse_releases,
                artist=artist_id,
                release_type=["album"],  # Server-side filter for Albums
                includes=["recordings", "release-groups"],
                limit=limit,
                offset=offset,
            )

            releases = resp.get("release-list", [])
            if not releases:
                break

            for release_info in releases:
                total_processed += 1

                # 1. Filter Release Status (Official only, no Bootlegs)
                # Logic update: Allow "Bootleg" if it IS NOT in reject_types
                # "Official" is always allowed.
                release_status = release_info.get("status")

                is_official = release_status == "Official"
                is_bootleg = release_status == "Bootleg"

                # Check if we should allow bootlegs
                allow_bootlegs = "Bootleg" not in reject_types

                if not is_official:
                    # If it's not official, the only other thing we accept is Bootleg,
                    # and ONLY if allowed.
                    if is_bootleg and allow_bootlegs:
                        pass  # Allowed
                    else:
                        continue

                # 2. Filter Release Group Types
                # release-group info is embedded thanks to includes=['release-groups']
                rg = release_info.get("release-group", {})
                primary = rg.get("primary-type")
                secondary = rg.get("secondary-type-list") or []

                # Primary must be Album (or EP if we wanted, but previous logic was strict Album)
                if primary != "Album":
                    continue

                # Strict filtering for Studio Albums
                # Reject these secondary types if they are in the reject list
                if set(secondary).intersection(reject_types):
                    continue

                # Use Release Group's first release date if available (better for canonical year), otherwise release date
                release_date_src = rg.get("first-release-date") or release_info.get(
                    "date", "????"
                )
                year = release_date_src[:4] if release_date_src else "????"

                # Append year to title for disambiguation (e.g. "Peter Gabriel (1977)")
                album_title = f"{release_info['title']} ({year})"

                # 3. Check for Covers
                cover_url = None
                if release_info.get("cover-art-archive", {}).get("front") == "true":
                    cover_url = f"http://coverartarchive.org/release/{release_info['id']}/front-250"

                if "medium-list" not in release_info:
                    continue

                # 4. Process Tracks
                for medium in release_info["medium-list"]:
                    if "track-list" not in medium:
                        continue
                    for track in medium["track-list"]:
                        if "recording" in track:
                            song_title = track["recording"]["title"]

                            norm = normalize_title(song_title)

                            # Check duplicates using O(1) lookup
                            if norm in normalized_lookup:
                                existing_title = normalized_lookup[norm]

                                # Prefer shorter title
                                if len(song_title) < len(existing_title):
                                    # We found a "better" version of the same song (shorter title)
                                    # Swap them out

                                    # 1. Pop old data
                                    data = new_songs.pop(existing_title)

                                    # 2. Update lookup to point to new title
                                    normalized_lookup[norm] = song_title

                                    # 3. Preserve/Update metadata
                                    if not cover_url and "cover_url" in data:
                                        cover_url = data["cover_url"]

                                    data["cover_url"] = cover_url
                                    data["album"] = album_title
                                    data["year"] = year

                                    # 4. Store under new title
                                    new_songs[song_title] = data
                                else:
                                    # Existing title is better or equal length.
                                    # Just update cover/album info if helpful.
                                    curr_data = new_songs[existing_title]
                                    if cover_url and "cover_url" not in curr_data:
                                        curr_data["cover_url"] = cover_url
                                        curr_data["album"] = album_title
                                        curr_data["year"] = year

                            else:
                                # New unique song
                                normalized_lookup[norm] = song_title
                                new_songs[song_title] = {
                                    "score": 1200,
                                    "matches": 0,
                                    "album": album_title,
                                    "year": year,
                                    "artist": real_name,
                                    "cover_url": cover_url,
                                }

            print(
                f"STATUS: Processed {total_processed} releases... (found {len(new_songs)} unique songs so far)"
            )

            # Robust pagination: intentionally simplistic
            # If we got any releases, advance offset by that amount.
            # If we got NO releases, we are done (handled by 'if not releases: break' above)
            offset += len(releases)

        except Exception as e:
            print(f"STATUS: Error fetching releases at offset {offset}: {e}")

            break

    return new_songs


def main():
    if len(sys.argv) < 2:
        print(json.dumps({}))
        sys.exit(1)

    # Mode: 'youtube' or defaults to artist search
    mode = sys.argv[1]

    if mode == "youtube":
        if len(sys.argv) < 3:
            sys.exit(1)
        query = sys.argv[2]

        # Youtube search implementation
        from youtubesearchpython import VideosSearch

        try:
            videosSearch = VideosSearch(query, limit=1)
            result = videosSearch.result()
            if result["result"]:
                print(result["result"][0]["link"])
            else:
                print("")
        except Exception:
            print("")

    elif mode == "itunes":
        if len(sys.argv) < 5:
            # Expected: script.py itunes artist song album
            sys.exit(1)

        artist = sys.argv[2]
        title = sys.argv[3]
        album = sys.argv[4]

        # iTunes Search Implementation
        try:
            # Construct a specific query
            # "Artist Song" is usually enough, but let's try to be specific
            term = f"{artist} {title}"
            params = {
                "term": term,
                "media": "music",
                "entity": "song",
                "limit": 5,  # Fetch a few to filter
            }
            resp = requests.get(
                "https://itunes.apple.com/search", params=params, timeout=10
            )
            data = resp.json()

            found_url = ""

            if data["resultCount"] > 0:
                results = data["results"]
                # 1. Try to find match with exact artist
                best_match = None

                # Normalize helper
                def norm(s):
                    return re.sub(r"[^a-z0-9]", "", str(s).lower())

                target_artist = norm(artist)
                target_album = norm(album)
                target_title = norm(title)

                for r in results:
                    r_artist = norm(r.get("artistName", ""))
                    r_track = norm(r.get("trackName", ""))
                    r_album = norm(r.get("collectionName", ""))

                    # Check artist match first
                    if target_artist in r_artist or r_artist in target_artist:
                        # Check title match
                        if target_title in r_track or r_track in target_title:
                            best_match = r
                            # If album also matches, it's a perfect match, stop looking
                            if target_album and (
                                target_album in r_album or r_album in target_album
                            ):
                                break

                # If we found a match, check if it has a preview Url
                if best_match:
                    found_url = best_match.get("previewUrl", "")
                elif results:
                    # Fallback to first result if we are desperate?
                    # No, better false negative than wrong song.
                    pass

            print(found_url)

        except Exception as e:
            # print(f"DEBUG: iTunes error: {e}")
            print("")

    else:
        # Artist Search Mode
        artist_name_arg = sys.argv[1]

        # Optional reject list
        reject_list_arg = []
        if len(sys.argv) > 2:
            reject_str = sys.argv[2]
            if reject_str:
                reject_list_arg = reject_str.split(",")

        try:
            songs = fetch_data(artist_name_arg, reject_list_arg)
            print(json.dumps(songs, indent=2))
        except Exception as e:
            print(f"STATUS: Error: {e}")

            print("{}")


if __name__ == "__main__":
    main()
