#!/usr/bin/env python3
"""ExploreAnywhere Phase 4E: safe, targeted named-destination search fix.

Run in the Django project root. This script changes only apps/places/views.py.
It never accesses the database and never changes MapTiler or migrations.
"""
from __future__ import annotations

import ast
import datetime as dt
import pathlib
import re
import shutil
import sys

PROJECT = pathlib.Path.cwd()
TARGET = PROJECT / 'apps' / 'places' / 'views.py'
MARKER = '# ExploreAnywhere Phase 4E named-destination search fix v1'

REPLACEMENT = '''def build_attraction_filter(search_text):
    """Match named Kabankalan places precisely; expand only broad category searches.

    The caller already limits records to verified, published Kabankalan places.
    Query-based filtering is separate from hobby/rating recommendation ranking.
    """
    # ExploreAnywhere Phase 4E named-destination search fix v1
    import unicodedata

    normalized = unicodedata.normalize(
        "NFKD", str(search_text or "")[:300]
    ).encode("ascii", "ignore").decode("ascii").lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    if not words:
        return None

    # City/province words are location qualifiers, not attraction keywords.
    # The view itself already enforces Kabankalan via city_id=2.
    location_words = {
        "kabankalan", "city", "negros", "occidental", "philippines",
    }
    filler_words = STOP_WORDS | {
        "attraction", "attractions", "destination", "destinations",
        "thing", "things", "do", "around", "within", "nearby",
        "spot", "spots", "tourist", "site", "sites", "best", "top",
        "looking", "from", "my", "and", "hopping", "activity", "activities",
    }
    keywords = list(dict.fromkeys(
        word for word in words
        if word not in location_words
        and word not in filler_words
        and len(word) >= 2
    ))

    # "places in Kabankalan" is a browse-all request, not a failed search.
    if not keywords:
        return None

    matched_intents = [
        name for name, intent in SEARCH_INTENTS.items()
        if any(word in intent["triggers"] for word in keywords)
    ]
    generic_words = {
        word
        for intent in SEARCH_INTENTS.values()
        for word in intent["triggers"] + intent["terms"]
    } | {
        "mount", "mountain", "mountains", "hill", "hills", "peak", "peaks",
        "plaza", "museum", "park", "parks", "trail", "trails", "river",
        "food", "photography", "gaming", "art", "culture", "shopping",
        "billiards", "basketball", "music", "swimming",
    }

    # A distinctive name token (Amyan, CPSU, Mag, Aso, Nai-guin, etc.) means
    # the visitor is looking for a particular place, not all places of a type.
    # Require every name token to appear in the title, preventing broad OR
    # matches from yielding nearly all places for "CPSU Museum".
    distinctive_words = [w for w in keywords if w not in generic_words]
    if distinctive_words:
        ignored_modifiers = {
            "nature", "hiking", "photography", "swimming", "beach",
            "beaches", "food", "eat", "cafe", "coffee", "shopping",
            "gaming", "music", "art", "culture",
        }
        name_words = [w for w in keywords if w not in ignored_modifiers]
        name_filter = Q()
        for word in name_words:
            name_filter &= Q(title__icontains=word)
        return name_filter

    # "Kabankalan Plaza" or "plaza in Kabankalan" should only find
    # the actual place title, not unrelated places mentioning Kabankalan.
    if "kabankalan" in words and not matched_intents:
        title_filter = Q()
        for word in keywords:
            title_filter &= Q(title__icontains=word)
        return title_filter

    # Broad searches such as "nature", "museum" and "waterfalls" can use
    # known types and matching text. Do not demand the correct category slug
    # alone, because some verified records still have a generic category.
    if matched_intents:
        category_slugs = {
            "beach": ("beach",),
            "waterfall": ("waterfall",),
            "history": (
                "museum", "memorial", "monument", "historic-ruins",
                "historic-fort", "archaeological-site",
            ),
        }
        terms = set()
        slugs = set()
        for name in matched_intents:
            terms.update(SEARCH_INTENTS[name]["terms"])
            slugs.update(category_slugs.get(name, ()))

        broad_filter = Q()
        if slugs:
            broad_filter |= Q(category__slug__in=sorted(slugs))
        for term in sorted(terms):
            broad_filter |= Q(title__icontains=term)
            broad_filter |= Q(description__icontains=term)
            broad_filter |= Q(address__icontains=term)
            broad_filter |= Q(category__name__icontains=term)
        return broad_filter

    # Plain terms such as "plaza" require a match to the supplied terms.
    # AND across words prevents location text from matching every destination.
    text_filter = Q()
    for word in keywords:
        text_filter &= (
            Q(title__icontains=word)
            | Q(description__icontains=word)
            | Q(address__icontains=word)
            | Q(barangay__icontains=word)
            | Q(category__name__icontains=word)
        )
    return text_filter

'''


def main():
    if not TARGET.is_file():
        raise SystemExit('ERROR: Run this script from your ExploreAnywhere project root (manage.py folder).')

    original_bytes = TARGET.read_bytes()
    try:
        original = original_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise SystemExit('ERROR: views.py is not UTF-8. No changes made.')

    if MARKER in original:
        print('ALREADY INSTALLED: Phase 4E search fix is present. No changes made.')
        return

    start_marker = 'def build_attraction_filter(search_text):'
    end_marker = '@login_required\ndef attraction_carousel(request):'
    if original.count(start_marker) != 1 or original.count(end_marker) != 1:
        raise SystemExit('ERROR: Expected search/view structure was not found. No changes made.')
    start = original.index(start_marker)
    end = original.index(end_marker, start)
    previous_function = original[start:end]
    required = ('SEARCH_INTENTS', 'Q(', 'category_slugs', 'return filters')
    if not all(token in previous_function for token in required):
        raise SystemExit('ERROR: Search function differs from reviewed source. No changes made.')

    newline = '\r\n' if b'\r\n' in original_bytes else '\n'
    replacement = REPLACEMENT.replace('\n', newline)
    updated = original[:start] + replacement + original[end:]
    try:
        ast.parse(updated, filename=str(TARGET))
        compile(updated, str(TARGET), 'exec')
    except (SyntaxError, ValueError) as exc:
        raise SystemExit(f'ERROR: Proposed Python failed syntax validation: {exc}')

    if '--dry-run' in sys.argv:
        print('DRY RUN OK: Phase 4E search fix can be applied; no files changed.')
        return

    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_dir = PROJECT / 'phase4_backups' / f'search-accuracy-{stamp}'
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_path = backup_dir / 'views.py'
    shutil.copy2(TARGET, backup_path)
    try:
        new_bytes = updated.encode('utf-8')
        if original_bytes.startswith(b'\xef\xbb\xbf'):
            new_bytes = b'\xef\xbb\xbf' + new_bytes
        TARGET.write_bytes(new_bytes)
    except Exception:
        shutil.copy2(backup_path, TARGET)
        raise

    print('SUCCESS: Phase 4E named-destination search repaired.')
    print('Fixed: Kabankalan Plaza, CPSU Museum, Mag Aso Falls and named-place searches.')
    print('Kept: broad nature/history/waterfall searches and existing recommendation scores.')
    print('Changed ONLY:', TARGET.relative_to(PROJECT))
    print('Backup:', backup_path.relative_to(PROJECT))
    print('No migrations, database records, routes, MapTiler keys, or templates modified.')
    print('Next: python manage.py check')
    print('Next: test searches for Kabankalan Plaza, CPSU Museum, Mag Aso Falls, nature.')


if __name__ == '__main__':
    main()
