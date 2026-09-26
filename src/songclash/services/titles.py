"""Track title normalization, shared by every metadata source."""

import re

# Words that mark a title as an alternate version of the same song.
VERSION_KEYWORDS = [
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
    "acoustic",
    "instrumental",
]
_KW = "|".join(VERSION_KEYWORDS)
_PAREN_RE = re.compile(r"\s*[\(\[][^\)\]]*?(?:" + _KW + r")[^\)\]]*?[\)\]]", re.I)
_SUFFIX_RE = re.compile(r"\s-\s.*?(?:" + _KW + r").*?$", re.I)
_BRACKETED_RE = re.compile(r"\s*[\(\[].*?[\)\]]")


def normalize_title(title: str) -> str:
    """Reduce a track title to a key shared by all versions of the song."""
    n = title.lower()
    n = n.replace("’", "'").replace("‘", "'").replace("`", "'")
    n = n.replace("“", '"').replace("”", '"')
    n = _PAREN_RE.sub("", n)
    n = _SUFFIX_RE.sub("", n)
    return " ".join(n.split())


def strip_brackets(title: str) -> str:
    """Drop every bracketed part: "Song (Live) [Mono]" -> "Song"."""
    return _BRACKETED_RE.sub("", title).strip(" .")


def alnum_key(text: str) -> str:
    """Lowercase letters and digits only, for fuzzy comparisons."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())
