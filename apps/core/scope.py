"""The content scope of ExploreKabankalan.

ExploreKabankalan serves **one city** with **two pillars** of public content:

1. **Places** (``apps.places``) - a real, mapped destination a visitor can
   choose *for a hobby or for a local errand*. Every published place carries
   a category from the taxonomy and at least one hobby, because the
   recommendation score is built on hobby fit.
2. **City Information** (``apps.info``) - short editorial facts about the
   city, written and published by staff.

Anything that is not one of those two things is **out of scope**. The most
common mistake is importing a whole class of civic institutions (schools,
hospitals, government offices) as "places": they are not destinations a
visitor picks for a hobby, they have no hobby, they cannot be recommended,
and they dilute the catalogue with rows the recommendation engine can never
surface.

This module is the single place where that rule is written down, so it can be
checked by code instead of remembered by a person. It is deliberately small
and free of database access: :mod:`apps.core.checks` and the
``check_content_scope`` / ``purge_off_scope_places`` commands use it to audit
a live installation.
"""
import re

#: The one city this system covers.
SCOPE_CITY_PK = 2

#: The system's purpose, in one sentence. Used by the audit commands so the
#: operator always sees what the catalogue is *for* while judging records.
SYSTEM_PURPOSE = (
    "ExploreKabankalan is a hobby-weighted directory of real places to visit "
    "in Kabankalan City, plus staff-published City Information notes."
)

#: The two pillars of public content.
PILLARS = (
    "Places: a real destination a visitor chooses for a hobby or a local errand.",
    "City Information: an editorial fact about the city, published by staff.",
)

#: Educational institutions are the canonical off-pillar record. They are not
#: destinations a visitor selects for a hobby, they carry no hobby, and the
#: recommendation score can never rank them. When the city administration
#: wants to mention one, it belongs in City Information as a single curated
#: fact - not as a bulk set of place rows.
INSTITUTION_PATTERNS = (
    (re.compile(r"\belementary\s+school\b", re.IGNORECASE), "elementary school"),
    (re.compile(r"\bhigh\s*school\b", re.IGNORECASE), "high school"),
    (re.compile(r"\bcollege\b", re.IGNORECASE), "college"),
    (re.compile(r"\bacademy\b", re.IGNORECASE), "academy"),
    (re.compile(r"\buniversity\b", re.IGNORECASE), "university"),
    (re.compile(r"\bseminary\b", re.IGNORECASE), "seminary"),
    (re.compile(r"\bvocational\s+school\b", re.IGNORECASE), "vocational school"),
    (re.compile(r"\btechnical\s+institute\b", re.IGNORECASE), "technical institute"),
)

#: Civic and institutional offices are reported for review but are **not**
#: removed automatically: some of them (a city hall, a public library) are
#: genuine landmarks a visitor photographs.
CIVIC_PATTERNS = (
    (re.compile(r"\bcity\s+hall\b", re.IGNORECASE), "city hall"),
    (re.compile(r"\bmunicipal\s+hall\b", re.IGNORECASE), "municipal hall"),
    (re.compile(r"\bpublic\s+library\b", re.IGNORECASE), "public library"),
    (re.compile(r"\bhealth\s+centre?\b", re.IGNORECASE), "health centre"),
    (re.compile(r"\bpolice\s+station\b", re.IGNORECASE), "police station"),
)


def institution_kind(title):
    """Return the kind of educational institution in ``title``, or ``""``."""
    for pattern, label in INSTITUTION_PATTERNS:
        if pattern.search(title or ""):
            return label
    return ""


def civic_kind(title):
    """Return the kind of civic office in ``title``, or ``""``."""
    for pattern, label in CIVIC_PATTERNS:
        if pattern.search(title or ""):
            return label
    return ""


def hobby_slugs(place):
    """Return the hobby slugs linked to ``place``.

    Accepts a Django model instance (the usual case) or any object that
    exposes a ``hobbies`` collection, so the rule can be unit tested without
    touching the database.
    """
    hobbies = getattr(place, "hobbies", None)
    if hobbies is None:
        return []
    if hasattr(hobbies, "all"):
        hobbies = hobbies.all()
    slugs = []
    for hobby in hobbies:
        slug = getattr(hobby, "slug", None)
        if slug:
            slugs.append(slug)
    return slugs


def place_violations(place):
    """Return the scope problems of a place, as a list of readable reasons.

    The reasons are ordered from "this record is the wrong shape for the
    system" to "this record is merely incomplete".
    """
    reasons = []

    kind = institution_kind(getattr(place, "title", ""))
    if kind:
        reasons.append(
            "educational institution (%s): not a destination a visitor picks "
            "for a hobby, so it can never be recommended" % kind
        )

    if getattr(place, "category_id", None) is None:
        reasons.append("no category: the place is not filed in the taxonomy")

    if not hobby_slugs(place):
        reasons.append(
            "no hobby: the recommendation score is 60% hobby fit, so the "
            "record can never be surfaced for a visitor"
        )

    if not (getattr(place, "description", "") or "").strip():
        reasons.append("no description")

    return reasons


def is_place_in_scope(place):
    """True when a place satisfies the Places pillar of the system."""
    return not place_violations(place)
