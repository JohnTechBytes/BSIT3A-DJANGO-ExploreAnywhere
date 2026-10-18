#!/usr/bin/env python3
"""ExploreAnywhere Phase 6I: retire redundant Hobby Selection safely.

Run from the Django project root. Makes a backup and validates Django before
accepting changes. Never changes migrations, settings, database, or MapTiler.
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

PHASE = 'ExploreAnywhere Phase 6I — One-Step Discovery'
MARKER = 'exploreanywhere-phase6i-hobby-step-retired'
SELECT_TAG = "{% url 'hobbies:select' %}"
SEARCH_TAG = "{% url 'hobbies:search' %}"
BROWSE_TAG = "{% url 'places:attraction_carousel' %}?browse=all"
PLACES_TAG = "{% url 'places:attraction_carousel' %}"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_text(path):
    raw = path.read_bytes()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    ending = '\r\n' if b'\r\n' in raw else '\n'
    return text, ending, has_bom


def encode(text, ending, bom):
    raw = text.replace('\n', ending).encode('utf-8')
    return b'\xef\xbb\xbf' + raw if bom else raw


def replace_function_bodies(source):
    if MARKER in source:
        return source
    tree = ast.parse(source)
    fn_names = {'hobby_selection', 'natural_language_search'}
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in fn_names]
    if {n.name for n in functions} != fn_names:
        raise ValueError('Expected hobby_selection and natural_language_search functions were not found; refusing to patch.')
    text_lines = source.splitlines(keepends=True)
    replacements = {
        'hobby_selection': '''def hobby_selection(request):
    """Legacy /hobbies/ route: Explore Places replaces the selection step."""
    from django.urls import reverse
    return redirect(reverse("places:attraction_carousel") + "?browse=all")
''',
        'natural_language_search': '''def natural_language_search(request):
    """Legacy /hobbies/search/: preserve old search queries without a wizard."""
    from urllib.parse import urlencode
    from django.urls import reverse
    query = (
        request.POST.get("query") or request.POST.get("q") or ""
        if request.method == "POST"
        else request.GET.get("q") or request.GET.get("query") or ""
    ).strip()[:200]
    params = {"q": query} if query else {"browse": "all"}
    return redirect(reverse("places:attraction_carousel") + "?" + urlencode(params))
''',
    }
    for node in sorted(functions, key=lambda n: n.lineno, reverse=True):
        text_lines[node.lineno-1: node.end_lineno] = [replacements[node.name]]
    return ''.join(text_lines) + '\n# ' + MARKER + '\n'


def patch_home(source):
    # Navbar Hobbies link is replaced by the single Explore Places entry.
    nav = re.compile(r'(?m)^\s*<a\s+class="nav-link"\s+href="' + re.escape(SELECT_TAG) + r'">\s*Hobbies\s*</a>\s*\n')
    source = nav.sub('\n', source)
    source = source.replace('href="' + SELECT_TAG + '"', 'href="' + BROWSE_TAG + '"')
    source = source.replace('action="' + SEARCH_TAG + '"', 'action="' + PLACES_TAG + '"')
    return source


def patch_base(source):
    nav = re.compile(r'(?m)^\s*<a\s+href="' + re.escape(SELECT_TAG) + r'">\s*Hobbies\s*</a>\s*\n')
    return nav.sub('\n', source)


def patch_carousel(source):
    # Keep the user's existing search, dropdown, scoring, and map behavior.
    if 'id="ea-filter-hobby"' not in source or 'id="ea-search-query"' not in source:
        raise ValueError('Explore Places search/hobby filters not found. Refusing to hide Hobby Selection until the replacement is present.')
    source = source.replace('href="' + SELECT_TAG + '"', 'href="#ea-filter-hobby"')
    source = source.replace('&#8592; Change Hobbies', 'Filter by hobby &#8595;')
    source = source.replace('href="' + SEARCH_TAG + '"', 'href="#ea-search-query"')
    return source


def patch_nearby(source):
    source = source.replace('href="' + SELECT_TAG + '"', 'href="' + BROWSE_TAG + '"')
    source = source.replace('← Change Hobbies', '← All Places')
    source = source.replace('&#8592; Change Hobbies', '&#8592; All Places')
    return source


def patch_views(source):
    # The existing score formula stays untouched. If a visitor deliberately
    # chooses a hobby from Explore Places, that choice drives relevance, even
    # without the old Hobby Selection session.
    sentinel = 'exploreanywhere-phase6i-inline-hobby-relevance'
    if sentinel in source:
        return source
    needle = '''    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        request.session.get("selected_hobbies", []),
    )'''
    repl = '''    # exploreanywhere-phase6i-inline-hobby-relevance
    # Use the Explore Places hobby dropdown without requiring a separate step.
    # If no filter is chosen, retain any previously saved preferences.
    scoring_hobbies = (
        [selected_hobby] if selected_hobby
        else request.session.get("selected_hobbies", [])
    )
    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        scoring_hobbies,
    )'''
    if source.count(needle) != 1:
        raise ValueError('Recommendation call changed since the source review; refusing to edit it.')
    source = source.replace(needle, repl)
    context = '''"selected_hobbies": request.session.get(
                "selected_hobbies", []
            ),'''
    if source.count(context) != 1:
        raise ValueError('Hobby-scoring template context changed; refusing to edit it.')
    return source.replace(context, '"selected_hobbies": scoring_hobbies,')


def general_template(source):
    # Fix the remaining saved-place, itinerary and Journey bookmarks/CTAs.
    # Never alter the old hobby wizard's unused templates themselves.
    return (source.replace('href="' + SELECT_TAG + '"', 'href="' + BROWSE_TAG + '"')
                  .replace('href="' + SEARCH_TAG + '"', 'href="' + BROWSE_TAG + '"'))


def build(root):
    targets = {
        'apps/hobbies/views.py': replace_function_bodies,
        'apps/places/views.py': patch_views,
        'templates/home.html': patch_home,
        'templates/theme/public_base.html': patch_base,
        'templates/places/attraction_carousel.html': patch_carousel,
        'templates/places/nearby_places.html': patch_nearby,
    }
    for name in targets:
        if not (root/name).is_file():
            raise ValueError(f'Missing required project file: {name}')
    edits = {}
    for name, fn in targets.items():
        p = root/name
        text, ending, bom = read_text(p)
        updated = fn(text)
        # Update any remaining old URLs in these files too, except custom anchors.
        updated = general_template(updated)
        if updated != text:
            edits[name] = encode(updated, ending, bom)
    # Catch other links in the latest installed Journey and other templates,
    # without disturbing Admin, the retired wizard, or credentials.
    for p in (root/'templates').rglob('*.html'):
        name = p.relative_to(root).as_posix()
        if name in targets or name.startswith(('templates/admin/', 'templates/hobbies/')):
            continue
        text, ending, bom = read_text(p)
        if SELECT_TAG not in text and SEARCH_TAG not in text:
            continue
        changed = general_template(text)
        if changed != text:
            edits[name] = encode(changed, ending, bom)
    if MARKER not in (root/'apps/hobbies/views.py').read_text(encoding='utf-8-sig'):
        if 'apps/hobbies/views.py' not in edits:
            raise ValueError('Legacy hobbies view did not change; refusing partial installation.')
    # Ensure Django modules stay valid before writing anything.
    for name, raw in edits.items():
        if name.endswith('.py'):
            compile(raw.decode('utf-8-sig'), name, 'exec')
    return edits


def run_check(root):
    cmds = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.urls import reverse; from django.template.loader import get_template; "
         "[reverse(n) for n in ('hobbies:select','hobbies:search','places:attraction_carousel')]; "
         "[get_template(n) for n in ('home.html','theme/public_base.html','places/attraction_carousel.html','places/nearby_places.html')]; "
         "print('PASS: URLs and templates')"],
    ]
    for cmd in cmds:
        print('VALIDATING:', ' '.join(cmd[1:]), flush=True)
        proc = subprocess.run(cmd, cwd=root, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=100)
        print(proc.stdout.strip()[-2000:], flush=True)
        if proc.returncode:
            raise RuntimeError(f'Django validation failed: exit {proc.returncode}')


def restore(root, folder, automatic=False):
    folder = Path(folder)
    if not folder.is_absolute():
        folder = root/folder
    manifest = folder/'manifest.json'
    if not manifest.is_file():
        raise ValueError('Backup manifest not found: '+str(manifest))
    info = json.loads(manifest.read_text(encoding='utf-8'))
    for item in info['files']:
        target = root/item['path']
        backup = folder/'original'/item['path']
        if not backup.exists():
            raise ValueError('Missing backup: '+str(backup))
        if not automatic and target.exists() and digest(target.read_bytes()) != item['after_sha256']:
            raise ValueError('Current file was edited since installation: '+item['path']+
                             '. Preserve newer edits before restoring.')
    for item in info['files']:
        dest = root/item['path'];dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(folder/'original'/item['path'], dest)
    print('RESTORED:', len(info['files']), 'original file(s) from', folder, flush=True)


def main():
    ap=argparse.ArgumentParser(description=PHASE)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--restore', help='Backup directory created by this script')
    args=ap.parse_args()
    root=Path.cwd().resolve()
    if not (root/'manage.py').is_file():
        ap.error('Open PowerShell in the ExploreAnywhere project directory (manage.py must exist).')
    if args.restore:
        restore(root,args.restore)
        return
    edits=build(root)
    if not edits:
        print('ALREADY INSTALLED: No additional changes necessary.')
        return
    print('READY:', PHASE)
    for name in edits:
        print('  ',name)
    print('Preserved: hobby tags and ranking formula, saved places, maps, verified-only filtering, database and migrations.')
    if args.dry_run:
        print('DRY RUN OK: No project files or database records changed.')
        return
    folder=root/'phase6_backups'/('no-hobby-wizard-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6])
    originals=folder/'original'
    files=[]
    for name, data in edits.items():
        path=root/name; backup=originals/name;backup.parent.mkdir(parents=True,exist_ok=True)
        old=path.read_bytes()
        backup.write_bytes(old)
        files.append({'path':name, 'before_sha256':digest(old),'after_sha256':digest(data)})
    (folder/'manifest.json').write_text(json.dumps({'phase':PHASE,'files':files},indent=2),encoding='utf-8')
    try:
        for name, data in edits.items():
            (root/name).write_bytes(data)
        run_check(root)
    except Exception as exc:
        print('INSTALLATION FAILED — restoring originals:',exc,flush=True)
        restore(root,folder,automatic=True)
        raise SystemExit(1)
    print('SUCCESS: Hobby Selection retired. /hobbies/ and /hobbies/search/ now redirect to Explore Places.')
    print('BACKUP:',folder.relative_to(root))
    print('RESTORE: python', repr(str(Path(__file__).resolve())), '--restore',repr(str(folder.relative_to(root))))
    print('NEXT: restart Django and test navbar, search, filters, and legacy hobby URLs.')


if __name__=='__main__':
    main()
