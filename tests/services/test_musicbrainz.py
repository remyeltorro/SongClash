import threading

import pytest

from songclash.services import musicbrainz
from songclash.services.errors import FetchCancelled


def _release(rid, date, titles, status="Official", front=True):
    return {
        "id": rid,
        "status": status,
        "date": date,
        "cover-art-archive": {"front": front},
        "media": [{"tracks": [{"title": t, "recording": {"title": t}} for t in titles]}],
    }


FAKE_GROUPS = [
    {
        "id": "g2",
        "title": "Second",
        "primary-type": "Album",
        "secondary-types": [],
        "first-release-date": "2002-01-01",
    },
    {
        "id": "g1",
        "title": "First",
        "primary-type": "Album",
        "secondary-types": [],
        "first-release-date": "2000-05-01",
    },
    {
        "id": "g3",
        "title": "Live!",
        "primary-type": "Album",
        "secondary-types": ["Live"],
        "first-release-date": "2003",
    },
    {
        "id": "g4",
        "title": "Boot",
        "primary-type": "Album",
        "secondary-types": [],
        "first-release-date": "2004",
    },
]
FAKE_RELEASES = {
    "g1": [
        _release("r1-deluxe", "2010-01-01", ["Opener", "Hit", "Hit (Demo)", "Bonus"]),
        _release("r1", "2000-05-01", ["Opener", "Hit (2010 Remaster)", "[silence]"], front=False),
    ],
    "g2": [_release("r2", "2002-01-01", ["Hit", "New Song"])],
    "g3": [_release("r3", "2003", ["Hit - Live"])],
    "g4": [_release("r4", "2004", ["Rare"], status="Bootleg")],
}


@pytest.fixture
def fake_mb(monkeypatch):
    def fake_get(self, endpoint, **params):
        if endpoint == "release-group":
            return {"release-groups": FAKE_GROUPS, "release-group-count": len(FAKE_GROUPS)}
        rels = FAKE_RELEASES[params["release-group"]]
        return {"releases": rels, "release-count": len(rels)}

    monkeypatch.setattr(musicbrainz.MusicBrainzClient, "get", fake_get)


def test_fetch_discography_dedupes_and_credits_original_album(fake_mb):
    songs = {s["title"]: s for s in musicbrainz.fetch_discography("id", "Band")}
    # The earliest release of "First" is used, so the deluxe bonus track is absent
    assert set(songs) == {"Opener", "Hit", "New Song"}
    assert songs["Hit"]["album"] == "First (2000)"
    assert songs["New Song"]["album"] == "Second (2002)"
    assert songs["Opener"]["cover_url"].endswith("/release-group/g1/front-250")


def test_fetch_discography_optional_types(fake_mb):
    songs = musicbrainz.fetch_discography("id", "Band", include_types=["Live"], include_bootlegs=True)
    assert "Rare" in {s["title"] for s in songs}


def test_album_without_cover_art(fake_mb, monkeypatch):
    monkeypatch.setitem(FAKE_RELEASES, "g2", [_release("r2", "2002", ["Solo"], front=False)])
    songs = {s["title"]: s for s in musicbrainz.fetch_discography("id", "Band")}
    assert songs["Solo"]["cover_url"] is None


def test_cancel_interrupts_waits():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(FetchCancelled):
        musicbrainz.MusicBrainzClient(cancel).get("artist", query="x")


def test_discography_options():
    opts = musicbrainz.discography_options(["EP", "Live", "Bootleg", "Nonsense"])
    assert opts == {"include_types": ["Live"], "include_eps": True, "include_bootlegs": True}
