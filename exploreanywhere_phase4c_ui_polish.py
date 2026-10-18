#!/usr/bin/env python3
"""ExploreAnywhere Phase 4C: UI-only polish of five verified Django templates.

Run from ExploreAnywhere project root with your normal virtual environment active:
    python "%USERPROFILE%\\Downloads\\exploreanywhere_phase4c_ui_polish.py"

No database/models/views/URLs/migrations are changed. Backups are created before writes.
The installer will stop if templates differ from the supplied Phase 4C source ZIP.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime

MARKER = "/* exploreanywhere-phase4c-polish-v1 */"

ROOTS = {
    "saved_places": Path("templates/places/saved_places.html"),
    "my_reviews": Path("templates/places/my_reviews.html"),
    "builder": Path("templates/itineraries/builder.html"),
    "my_itineraries": Path("templates/itineraries/my_itineraries.html"),
    "my_visits": Path("templates/visits/my_visits.html"),
}

# Exact SHA-256 values of the user's uploaded ExploreAnywhere_Phase4C_UI.zip.
# They prevent applying a stale patch over a newer or modified version.
EXPECTED = {
    "saved_places": "97a57e15b96497925bfe8312336f07f1ebc174b57f2a854864d0179fdd901814",
    "my_reviews": "beea6e8bb8bddf1dcf0eef75aaf3ce6921da3b79d511895fe8d3f32043a6eec7",
    "builder": "4249f6b8d5bb003689c92022bb25d9bfe45436f0d6d22efa8117ae05865349be",
    "my_itineraries": "c24e35cb429362049d73d3e24c4e9326d432799a0df8f6115d0c04eb545432b5",
    "my_visits": "628de5d243f24e3341c36ac1aa799370fdf1ed0fdd56cb29efd85471d3603871",
}

GLOBAL_CSS = r"""
/* exploreanywhere-phase4c-polish-v1 */
/* Scoped to these Phase 4C screens: existing forms and links are unchanged. */
.ea-saved,.ea-myreviews,.ea-trip,.ea-visits {
  --ea-c-navy:#102f59;--ea-c-blue:#075ee4;--ea-c-text:#19375e;
  --ea-c-muted:#63758d;--ea-c-border:#dce7f4;--ea-c-soft:#f5f9ff;
  --ea-c-shadow:0 12px 32px rgba(16,47,89,.075);
  font-family:inherit;line-height:1.55;min-width:0;
}
.ea-saved a,.ea-myreviews a,.ea-trip a,.ea-visits a {text-underline-offset:3px}
.ea-saved :is(a,button):focus-visible,.ea-myreviews :is(a,button):focus-visible,
.ea-trip :is(a,button,input,select,textarea):focus-visible,
.ea-visits :is(a,button):focus-visible {
  outline:3px solid #f6b83b;outline-offset:3px;
}
.ea-saved .ea-c-page-hero,.ea-myreviews .ea-c-page-hero,
.ea-visits .ea-c-page-hero {
  background:radial-gradient(circle at 91% 15%,rgba(133,198,255,.29),transparent 32%),
    linear-gradient(115deg,#102e5b,#075ee4);
  padding:clamp(24px,5vw,40px);border-radius:22px;color:#fff;
  box-shadow:0 20px 46px rgba(7,94,228,.13);margin-bottom:24px;
}
.ea-saved .ea-c-page-hero h1,.ea-myreviews .ea-c-page-hero h1,
.ea-visits .ea-c-page-hero h1 {color:#fff;font-size:clamp(29px,4vw,43px);margin:7px 0 8px;letter-spacing:-.035em;line-height:1.15}
.ea-saved .ea-c-page-hero p,.ea-myreviews .ea-c-page-hero p,
.ea-visits .ea-c-page-hero p {color:#e6f1ff;margin:0;max-width:68ch;line-height:1.65}
.ea-saved .ea-c-page-hero .ea-c-eyebrow,.ea-myreviews .ea-c-page-hero .ea-c-eyebrow,
.ea-visits .ea-c-page-hero .ea-c-eyebrow {
  color:#bbddff;font-size:12px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;
}
.ea-saved .ea-c-count,.ea-myreviews .ea-c-count {
  display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.24);
  padding:5px 12px;border-radius:999px;color:#fff;font-size:12px;font-weight:750;margin-top:14px;
}
.ea-saved .ea-action,.ea-myreviews .ea-myr-btn,.ea-visits .ea-visits-link,
.ea-trip .btn {transition:box-shadow .18s ease,transform .18s ease,background .18s ease}
.ea-saved .ea-action:hover,.ea-myreviews .ea-myr-btn:hover,
.ea-visits .ea-visits-link:hover,.ea-trip .btn:hover {transform:translateY(-1px);box-shadow:0 5px 15px rgba(7,94,228,.12)}
@media(max-width:700px){
  .ea-saved,.ea-myreviews,.ea-visits,.ea-trip {padding:24px 14px 70px}
  .ea-saved .ea-c-page-hero,.ea-myreviews .ea-c-page-hero,.ea-visits .ea-c-page-hero{border-radius:17px;padding:25px 20px}
  .ea-saved .ea-actions,.ea-myreviews .ea-myr-actions,.ea-visits .ea-visits-nav{gap:9px}
}
@media(prefers-reduced-motion:reduce){
  .ea-saved .ea-action,.ea-myreviews .ea-myr-btn,.ea-visits .ea-visits-link,.ea-trip .btn {transition:none}
  .ea-saved .ea-action:hover,.ea-myreviews .ea-myr-btn:hover,.ea-visits .ea-visits-link:hover,.ea-trip .btn:hover{transform:none}
}
"""

PAGE_CSS = {
"saved_places": r"""
.ea-saved{max-width:1180px}
.ea-saved-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,270px),1fr));gap:20px;align-items:stretch}
.ea-saved-item{gap:12px;overflow:hidden;border-radius:18px;padding:0;box-shadow:var(--ea-c-shadow);transition:box-shadow .18s ease,transform .18s ease}
.ea-saved-item:hover{box-shadow:0 18px 35px rgba(16,47,89,.14);transform:translateY(-2px)}
.ea-saved-item>:not(.ea-c-place-media){margin-left:19px;margin-right:19px}
.ea-saved-item>.ea-c-place-media{margin-bottom:3px;flex:none;height:178px;background:linear-gradient(140deg,#d8eaff,#d4e9df);position:relative;overflow:hidden}
.ea-c-place-media img{width:100%;height:100%;object-fit:cover;display:block}
.ea-c-place-media .ea-c-photo-empty{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;color:#375f86}
.ea-c-photo-empty .ea-c-photo-icon{font-size:34px;line-height:1}
.ea-c-place-media .ea-c-photo-empty span:last-child{font-size:12px;font-weight:750}
.ea-saved-item h2{font-size:20px;line-height:1.3}
.ea-saved-item p{line-height:1.6}
.ea-saved-item .ea-action{display:block;text-align:center;margin-top:auto;margin-bottom:0}
.ea-saved-item .ea-action+.ea-action{margin-top:0}
.ea-saved-item form{margin:0 19px 20px!important}
.ea-saved-item .ea-unsave{min-height:44px;border-color:#e5b8c0;color:#982e40;background:#fff6f7}
.ea-saved-item .ea-unsave:hover{background:#ffe8ec}
.ea-saved .ea-empty{background:var(--ea-c-soft);padding:clamp(28px,5vw,52px);text-align:center}
.ea-saved .ea-empty h2{font-size:23px;font-weight:800;color:var(--ea-c-navy)}
@media(max-width:700px){.ea-saved-grid{grid-template-columns:1fr}.ea-saved-item:hover{transform:none}}
""",
"my_reviews": r"""
.ea-myreviews{max-width:1060px}
.ea-myr-card{border-radius:19px;padding:clamp(19px,3vw,28px);box-shadow:var(--ea-c-shadow);margin:17px 0}
.ea-myr-card h2{font-size:22px;line-height:1.3;margin:0 0 10px}
.ea-myr-stars{display:inline-flex;background:#eaf2ff;color:#0755bd;padding:6px 12px;border-radius:999px;font-size:13px;gap:5px;align-items:center}
.ea-myr-card small{color:#64748b;margin-left:8px;font-size:12px}
.ea-myr-card p{white-space:normal;overflow-wrap:anywhere}
.ea-myr-card .ea-myr-btn{margin-top:7px}
.ea-myr-actions{margin:22px 0 26px}
.ea-myr-empty{border-radius:19px;padding:clamp(28px,5vw,48px);background:var(--ea-c-soft);text-align:center}
.ea-myr-empty h2{font-size:22px;color:var(--ea-c-navy);font-weight:800}
@media(max-width:560px){.ea-myr-card small{display:block;margin:8px 0 0}.ea-myr-actions a{flex:1;text-align:center}}
""",
"builder": r"""
.ea-trip{max-width:1180px}
.ea-trip .hero{padding:clamp(24px,4vw,40px);border-radius:22px;background:radial-gradient(circle at 91% 10%,rgba(170,214,255,.25),transparent 32%),linear-gradient(115deg,#102e5b,#075ee4);box-shadow:0 18px 40px rgba(7,94,228,.13)}
.ea-trip .hero h1{font-size:clamp(29px,4.2vw,43px);line-height:1.18;letter-spacing:-.025em;margin:8px 0 10px;overflow-wrap:anywhere}
.ea-trip .hero p:first-child{font-size:12px;font-weight:800;letter-spacing:.09em;color:#d5e7ff}
.ea-trip .panel{border-radius:19px;padding:clamp(18px,2.8vw,27px);box-shadow:var(--ea-c-shadow)}
.ea-trip .grid{gap:19px;align-items:start}
.ea-trip .trip-cards{grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:18px}
.ea-trip .field label{font-weight:800;color:#294869}
.ea-trip input,.ea-trip select,.ea-trip textarea{min-height:44px;border-radius:11px;border-color:#becfe6}
.ea-trip input:focus,.ea-trip select:focus,.ea-trip textarea:focus{border-color:#075ee4;box-shadow:0 0 0 3px #e2efff;outline:none}
.ea-trip .btn{min-height:44px;border-radius:11px}
.ea-trip .stop{border-left:0;border-top:5px solid #075ee4;display:flex;flex-direction:column;gap:5px}
.ea-trip .stop .stop-head{align-items:flex-start;margin-bottom:8px}
.ea-trip .stop .mini-actions{flex:none}
.ea-trip .stop .mini-actions button{min-width:42px;padding:8px 12px;font-size:18px}
.ea-trip .stop .actions{margin-top:auto}
.ea-trip .stop form:not(.mini-actions form) .field{min-width:0}
.ea-trip .pill{padding:6px 12px;font-size:12px}
.ea-trip .empty{background:var(--ea-c-soft);padding:32px;border-radius:18px}
.ea-trip .messages li{border-left:4px solid #075ee4}
@media(max-width:720px){.ea-trip .grid{grid-template-columns:1fr}.ea-trip .trip-cards{grid-template-columns:1fr}.ea-trip .stop-head{flex-wrap:wrap}}
""",
"my_itineraries": r"""
.ea-trip{max-width:1180px}
.ea-trip .hero{padding:clamp(24px,4vw,40px);border-radius:22px;background:radial-gradient(circle at 91% 10%,rgba(170,214,255,.25),transparent 32%),linear-gradient(115deg,#102e5b,#075ee4);box-shadow:0 18px 40px rgba(7,94,228,.13)}
.ea-trip .hero h1{font-size:clamp(29px,4.2vw,43px);line-height:1.18;letter-spacing:-.025em;margin:8px 0 10px}
.ea-trip .hero p:first-child{font-size:12px;font-weight:800;letter-spacing:.09em;color:#d5e7ff}
.ea-trip .trip-cards{grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:20px}
.ea-trip .trip-cards .panel{display:flex;flex-direction:column;align-items:flex-start;gap:9px;margin:0}
.ea-trip .trip-cards .panel p{margin:0}
.ea-trip .trip-cards .panel .btn{margin-top:auto}
.ea-trip .panel{border-radius:19px;padding:clamp(19px,3vw,28px);box-shadow:var(--ea-c-shadow)}
.ea-trip .trip-cards h2{font-size:22px;line-height:1.3;margin:5px 0;overflow-wrap:anywhere}
.ea-trip .btn{border-radius:11px;min-height:44px}
.ea-trip .pill{font-size:12px;padding:7px 13px}
.ea-trip .empty{background:var(--ea-c-soft);padding:clamp(25px,5vw,45px);border-radius:19px}
.ea-trip .messages li{border-left:4px solid #075ee4}
@media(max-width:720px){.ea-trip .trip-cards{grid-template-columns:1fr}}
""",
"my_visits": r"""
.ea-visits{max-width:1160px}
.ea-visits-nav{margin:22px 0 25px}
.ea-visits-stats{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:26px 0 34px}
.ea-visits-stat{padding:24px;border-radius:18px;box-shadow:var(--ea-c-shadow)}
.ea-visits-stat strong{font-size:clamp(29px,4vw,39px);line-height:1.2;margin-bottom:9px;letter-spacing:-.03em}
.ea-visits>h2{margin:30px 0 15px;color:var(--ea-c-navy);font-size:clamp(20px,2.4vw,25px);font-weight:850}
.ea-visit-badges{grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:14px}
.ea-visit-badge{padding:21px;border-radius:17px;background:#f8fafc;color:#64748b}
.ea-visit-badge.earned{background:#f1fcf6;color:#155e3e}
.ea-visit-badge strong{font-size:15px;line-height:1.35}
.ea-visit-badge p{font-size:13px;margin:8px 0 0;color:inherit}
.ea-visit-card{padding:clamp(20px,3vw,29px);border-radius:19px;box-shadow:var(--ea-c-shadow);margin:16px 0}
.ea-visit-card h2{font-weight:800;color:var(--ea-c-navy);font-size:21px}
.ea-visit-card p{overflow-wrap:anywhere}
.ea-visit-status{margin:4px 0 12px;font-size:12px;padding:7px 12px}
.ea-visit-card .ea-visits-link{margin-top:6px}
.ea-visits .ea-empty{padding:clamp(27px,5vw,45px);background:var(--ea-c-soft);text-align:center}
@media(max-width:700px){.ea-visits-stats{grid-template-columns:1fr;gap:10px}.ea-visits-stat{padding:17px 20px}.ea-visits-stat strong{font-size:31px}}
""",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Unexpected template structure ({label}): found {count} matches; expected one. No files changed.")
    return text.replace(old, new, 1)


def transform(name: str, original: str) -> str:
    if MARKER in original:
        raise ValueError(f"{name} already has the Phase 4C styles installed.")
    changed = replace_once(original, "</style>", GLOBAL_CSS + PAGE_CSS[name] + "\n</style>", f"{name} CSS")
    if name == "saved_places":
        before = '  <p class="ea-muted">MY KABANKALAN JOURNEY</p>\n  <h1>Saved Places</h1>\n  <p class="ea-muted">Your personal collection of published Kabankalan destinations.</p>'
        after = '''  <header class="ea-c-page-hero">
    <p class="ea-c-eyebrow">MY KABANKALAN JOURNEY</p>
    <h1>Saved Places</h1>
    <p>Your personal collection of published Kabankalan destinations.</p>
    <span class="ea-c-count">{{ entries|length }} saved destination{{ entries|length|pluralize }}</span>
  </header>'''
        changed = replace_once(changed, before, after, "saved hero")
        media = '''      <div class="ea-c-place-media">
        {% if entry.place.cover_image %}
          <img src="{{ entry.place.cover_image.url }}" alt="{{ entry.place.title }}" loading="lazy">
        {% elif entry.place.cover_image_url %}
          <img src="{{ entry.place.cover_image_url }}" alt="{{ entry.place.title }}" loading="lazy">
        {% else %}
          <div class="ea-c-photo-empty"><span class="ea-c-photo-icon" aria-hidden="true">&#128205;</span><span>No destination photo available</span></div>
        {% endif %}
      </div>'''
        changed = replace_once(changed, '    <article class="ea-saved-item">\n      <h2>', '    <article class="ea-saved-item">\n' + media + '\n      <h2>', "saved card media")
    elif name == "my_reviews":
        before = '  <p>MY KABANKALAN JOURNEY</p><h1>My Reviews</h1>\n  <p>Your ratings and experiences with Kabankalan destinations.</p>'
        after = '''  <header class="ea-c-page-hero">
    <p class="ea-c-eyebrow">MY KABANKALAN JOURNEY</p>
    <h1>My Reviews</h1>
    <p>Your ratings and experiences with Kabankalan destinations.</p>
    <span class="ea-c-count">{{ reviews|length }} submitted review{{ reviews|length|pluralize }}</span>
  </header>'''
        changed = replace_once(changed, before, after, "reviews hero")
        changed = replace_once(changed, '<span class="ea-myr-stars">{{ review.rating }} / 5 stars</span>', '<span class="ea-myr-stars" aria-label="Rated {{ review.rating }} out of 5 stars">&#9733; {{ review.rating }} / 5 stars</span>', "review rating")
    elif name == "my_visits":
        before = '  <p>ONE CITY. YOUR HOBBIES. OUR MAP.</p><h1>My Kabankalan Visits</h1>\n  <p>Only staff-approved destination check-ins earn points and badges. A visit report, saved place, map view, or submitted review does not verify physical presence.</p>'
        after = '''  <header class="ea-c-page-hero">
    <p class="ea-c-eyebrow">ONE CITY. YOUR HOBBIES. OUR MAP.</p>
    <h1>My Kabankalan Visits</h1>
    <p>Only staff-approved destination check-ins earn points and badges. A visit report, saved place, map view, or submitted review does not verify physical presence.</p>
  </header>'''
        changed = replace_once(changed, before, after, "visits hero")
    return changed


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    cwd = Path.cwd().resolve()
    if not (cwd / "manage.py").is_file():
        print("ERROR: Run this from the ExploreAnywhere project directory (with manage.py).")
        return 1

    # Preflight ALL templates before any writing or backup.
    originals: dict[str, bytes] = {}
    updates: dict[str, bytes] = {}
    already = 0
    failures: list[str] = []
    for name, relative in ROOTS.items():
        path = cwd / relative
        if not path.is_file():
            failures.append(f"Missing: {relative}")
            continue
        raw = path.read_bytes()
        originals[name] = raw
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            failures.append(f"Not UTF-8: {relative}")
            continue
        if MARKER in text:
            already += 1
            continue
        actual = sha256(raw)
        if actual != EXPECTED[name]:
            failures.append(f"Changed since upload: {relative} (SHA-256 mismatch)")
            continue
        try:
            updated = transform(name, text)
            # Existing navigation/POST forms and Django controls must not disappear.
            base_tags = re.findall(r"\{%.*?%\}", text, flags=re.S)
            new_tags = re.findall(r"\{%.*?%\}", updated, flags=re.S)
            for tag in set(base_tags):
                if new_tags.count(tag) < base_tags.count(tag):
                    raise ValueError(f"Lost template tag: {tag}")
            if updated.count("<style") != text.count("<style") or updated.count("</style>") != text.count("</style>"):
                raise ValueError("CSS tag count mismatch")
            updates[name] = updated.encode("utf-8")
        except ValueError as exc:
            failures.append(f"Unable to patch {relative}: {exc}")

    if failures:
        print("STOPPED SAFELY: No files changed.")
        for fail in failures:
            print(" -", fail)
        print("If you have changed templates since creating the Phase 4C ZIP, upload the newer templates so the patch can be updated.")
        return 1
    if already == len(ROOTS):
        print("ALREADY INSTALLED: All five Phase 4C UI templates are updated. No files changed.")
        return 0
    if already:
        print("STOPPED SAFELY: Some templates are already updated but others are not. No files changed.")
        return 1
    if len(updates) != len(ROOTS):
        print("ERROR: Preflight did not produce five updates; no files changed.")
        return 1
    if "--check" in sys.argv:
        print("READY: All five templates match the supplied source ZIP. No changes made (--check).")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = cwd / "phase4_backups" / f"ui-polish-{stamp}"
    for name, rel in ROOTS.items():
        backup_path = backup / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes(originals[name])

    changed: list[str] = []
    try:
        for name, rel in ROOTS.items():
            target = cwd / rel
            # Atomic replacement, avoiding partially written templates.
            with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".phase4c-", suffix=".tmp", delete=False) as tmp:
                temp_name = tmp.name
                tmp.write(updates[name])
            try:
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            changed.append(name)
    except Exception as exc:
        print("ERROR during installation:", exc)
        print("Restoring files from backups...")
        for name in changed:
            shutil.copy2(backup / ROOTS[name], cwd / ROOTS[name])
        return 1

    print("SUCCESS: Phase 4C UI polish installed across five templates.")
    print("Updated: Saved Places, My Reviews, Itinerary Builder, My Itineraries, My Visits.")
    print("Preserved: Django forms, POST/CSRF, routes, counts, status logic, and user data.")
    print("New photo handling: real destination images only, otherwise a neutral placeholder.")
    print("Backups:", backup.relative_to(cwd))
    print("No model, database, migration, view, or MapTiler key changes.")
    print("Next: python manage.py check")
    print('Next: python manage.py shell -c "from django.template.loader import get_template; [get_template(t) for t in [\'places/saved_places.html\',\'places/my_reviews.html\',\'itineraries/builder.html\',\'itineraries/my_itineraries.html\',\'visits/my_visits.html\']]; print(\'Templates OK\')"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
