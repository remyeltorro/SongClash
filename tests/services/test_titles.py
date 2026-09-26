import pytest

from songclash.services.titles import alnum_key, normalize_title, strip_brackets


@pytest.mark.parametrize(
    "a,b",
    [
        ("Something (Remastered 2009)", "Something"),
        ("Help! - Live at the BBC", "Help!"),
        ("Don’t Stop", "Don't Stop"),
        ("Song [Mono Version]", "song"),
    ],
)
def test_normalize_title_groups_versions(a, b):
    assert normalize_title(a) == normalize_title(b)


def test_normalize_keeps_distinct_songs_apart():
    assert normalize_title("Love (Is All)") != normalize_title("Love")


def test_strip_brackets():
    assert strip_brackets("Backdrifts. (Honeymoon Is Over.)") == "Backdrifts"
    assert strip_brackets("Song [Live] (Mono)") == "Song"


def test_alnum_key():
    assert alnum_key("AC/DC") == "acdc"
