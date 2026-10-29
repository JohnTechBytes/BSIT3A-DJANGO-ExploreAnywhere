"""Find and attach licensed Wikimedia Commons photos to Kabankalan places.

The public site must never show a photo it cannot attribute. This module only
accepts candidates that:

* come from a location-qualified Commons search,
* carry a licence from a small allow-list of free licences,
* live on ``upload.wikimedia.org`` / ``commons.wikimedia.org``,
* and whose file title contains every significant word of the place name.

Anything else is reported back as "no confident match" instead of being used.
The network calls themselves live in the existing Phase 6O helpers so the
rate-limit, retry and URL-trust rules stay in one place.
"""

from __future__ import annotations

import os
import re
import unicodedata

# Free licences that allow reuse with attribution. Anything else is skipped.
ALLOWED_LICENSES = {
    "CC BY 4.0",
    "CC BY 3.0",
    "CC BY 2.0",
    "CC BY-SA 4.0",
    "CC BY-SA 3.0",
    "CC BY-SA 2.0",
    "CC0 1.0",
    "Public domain",
}

STOPWORDS = {"the", "and", "of", "de", "del", "la", "las", "los", "sa", "ng", "at"}

# Commons file names often abbreviate these words.
TOKEN_ALIASES = {
    "mount": ("mt", "mtn"),
    "saint": ("st", "sto", "sta"),
    "barangay": ("brgy",),
    "falls": ("waterfall", "waterfalls"),
}

# Each search costs one volunteer-run API request; keep the budget small.
QUERIES_PER_PLACE = 2
CANDIDATES_PER_QUERY = 8


def user_agent() -> str:
    """Wikimedia asks for a real contact string; never invent a fake one."""
    return (os.environ.get("WIKIMEDIA_USER_AGENT") or "").strip()


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def name_tokens(title: str) -> tuple[str, ...]:
    """Significant words that a candidate file title must contain."""
    words = [word for word in normalize(title).split() if len(word) > 2 and word not in STOPWORDS]
    return tuple(dict.fromkeys(words))


def title_matches(place_title: str, file_title: str) -> bool:
    """True when every significant place word appears in the file name."""
    tokens = name_tokens(place_title)
    if not tokens:
        return False
    haystack = normalize(file_title)
    words = set(haystack.split())
    for token in tokens:
        variants = (token,) + TOKEN_ALIASES.get(token, ())
        if not any(variant in haystack or variant in words for variant in variants):
            return False
    return True


def licence_is_allowed(licence: str) -> bool:
    return normalize(licence) in {normalize(value) for value in ALLOWED_LICENSES}


def find_photo(place, *, search, queries_for, per_query: int = CANDIDATES_PER_QUERY,
               agent: str | None = None) -> tuple[dict | None, str]:
    """Return ``(candidate, reason)`` for the first confident, licensed match."""
    agent = agent or user_agent()
    if not agent:
        return None, "WIKIMEDIA_USER_AGENT is not set, so Wikimedia cannot be queried."

    queries = list(queries_for(place.title))[:QUERIES_PER_PLACE]
    if not queries:
        return None, "No searchable name."

    seen = 0
    for query in queries:
        try:
            candidates = search(query, agent, per_query) or []
        except Exception as error:  # network/permission problems must not abort a batch
            return None, f"Search failed: {type(error).__name__}"

        for candidate in candidates:
            seen += 1
            if not licence_is_allowed(candidate.get("license", "")):
                continue
            if not title_matches(place.title, candidate.get("file_title", "")):
                continue
            return candidate, "Matched by name and licence."

    return None, f"No confident match among {seen} candidate file(s)."


PHOTO_FIELDS = ("cover_image_url", "photo_credit", "photo_source_url",
                "photo_license", "photo_license_url")


def apply_photo(place, candidate: dict) -> None:
    place.cover_image_url = candidate.get("image_url", "")[:200]
    place.photo_credit = (candidate.get("credit") or "")[:200]
    place.photo_source_url = candidate.get("source_url", "")[:200]
    place.photo_license = (candidate.get("license") or "")[:120]
    place.photo_license_url = candidate.get("license_url", "")[:200]
    place.save(update_fields=list(PHOTO_FIELDS))
