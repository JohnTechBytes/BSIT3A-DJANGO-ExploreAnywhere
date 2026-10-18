#!/usr/bin/env python3
"""ExploreAnywhere: navigate Explore Places directly to published Kabankalan places.

From the Django project root, run:
  python path/to/exploreanywhere_fix_explore_places_direct.py --dry-run
  python path/to/exploreanywhere_fix_explore_places_direct.py

Only changes apps/places/views.py, templates/theme/public_base.html, and
 templates/home.html. Guards changes, makes backups, and does not touch DB.
"""
from __future__ import annotations
import ast
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
VIEWS = ROOT / 'apps' / 'places' / 'views.py'
BASE = ROOT / 'templates' / 'theme' / 'public_base.html'
HOME = ROOT / 'templates' / 'home.html'
FILES = (VIEWS, BASE, HOME)
MARK = '# exploreanywhere-phase4f-direct-place-browse-v1'
LINK_TARGET = "{% url 'places:attraction_carousel' %}?browse=all"


def stop(message):
    raise SystemExit('SAFETY STOP: ' + message + ' No files changed.')


def hobby_session_redirect(node, raw):
    if not isinstance(node, ast.If) or node.orelse or len(node.body) != 1:
        return False
    condition = ast.get_source_segment(raw, node.test) or ''
    if 'hobbies_city_id' not in condition or 'selected_hobbies' not in condition:
        return False
    body = node.body[0]
    if not isinstance(body, ast.Return):
        return False
    call = body.value
    return (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == 'redirect' and len(call.args) == 1
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == 'hobbies:select')


def fix_view(raw):
    if MARK in raw:
        return raw, 'already updated'
    try:
        tree = ast.parse(raw, filename=str(VIEWS))
    except SyntaxError as exc:
        stop('views.py cannot be parsed: ' + str(exc))
    funcs = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'attraction_carousel']
    if len(funcs) != 1:
        stop('Expected exactly one attraction_carousel function.')
    func = funcs[0]
    fsource = ast.get_source_segment(raw, func) or ''
    for required in ('login_required', 'is_active=True', 'is_verified=True', 'city=city', 'rank_kabankalan_places'):
        if required not in (fsource + ' ' + ' '.join(ast.get_source_segment(raw, d) or '' for d in func.decorator_list)):
            stop('Expected safety/ranking guard missing from attraction_carousel: ' + required)
    guards = [x for x in func.body if hobby_session_redirect(x, raw)]
    if len(guards) != 1:
        stop('Cannot uniquely identify the existing hobby-session redirect inside attraction_carousel.')
    guard = guards[0]
    query_assigns = [x for x in func.body if isinstance(x, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'search_query' for t in x.targets)]
    if len(query_assigns) != 1 or query_assigns[0].lineno <= guard.end_lineno:
        stop('Cannot safely locate the search_query assignment after the hobby redirect.')
    lines = raw.splitlines(keepends=True)
    newline = '\r\n' if '\r\n' in raw else '\n'
    edits = [
        (guard.lineno - 1, guard.end_lineno,
         ['    ' + MARK + newline,
          '    # Browse published Kabankalan places without requiring a hobby session.' + newline]),
        (query_assigns[0].lineno - 1, query_assigns[0].lineno - 1,
         ['    # The navbar Explore Places link resets only the previous text search.' + newline,
          '    # Keep chosen hobbies so a visitor can still see personalized scores.' + newline,
          '    if request.GET.get("browse") == "all":' + newline,
          '        request.session.pop("attraction_search_query", None)' + newline,
          newline])
    ]
    for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
        lines[start:end] = replacement
    result = ''.join(lines)
    try:
        compile(result, str(VIEWS), 'exec')
    except SyntaxError as exc:
        stop('Patched view fails syntax check: ' + str(exc))
    return result, 'removed hobby redirect and added browse-all reset'


# Only change nav links with the visible text "Explore Places"; keep Hobbies unchanged.
NAV_LINK = re.compile(r'(<a\b[^>]*?\bhref=")\{% url \'hobbies:select\' %\}("[^>]*>\s*Explore Places\s*</a>)', re.I)


def fix_template(raw, path):
    if LINK_TARGET in raw and not NAV_LINK.search(raw):
        return raw, 'already updated'
    new, count = NAV_LINK.subn(lambda m: m.group(1) + LINK_TARGET + m.group(2), raw)
    if count != 1:
        stop(f'{path.relative_to(ROOT)}: expected one navbar Explore Places link, found {count}.')
    if """{% url 'hobbies:select' %}">Hobbies</a>""" not in new:
        stop(f'{path.relative_to(ROOT)}: Hobbies navigation link not found; refusing to continue.')
    return new, 'Explore Places links directly to all Kabankalan destinations'


def main():
    if not (ROOT / 'manage.py').is_file():
        stop('Run from your ExploreAnywhere project directory containing manage.py.')
    for path in FILES:
        if not path.is_file():
            stop('Missing source file: ' + str(path))
    original = {}
    planned = {}
    notes = {}
    boms = {}
    for path in FILES:
        original[path] = path.read_bytes()
        boms[path] = original[path].startswith(b'\xef\xbb\xbf')
        try:
            raw = original[path].decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            stop(str(path) + ': ' + str(exc))
        updated, note = fix_view(raw) if path == VIEWS else fix_template(raw, path)
        notes[path] = note
        planned[path] = (b'\xef\xbb\xbf' if boms[path] else b'') + updated.encode('utf-8')
    changed = [path for path in FILES if planned[path] != original[path]]
    if not changed:
        print('ALREADY FIXED: Explore Places points to published Kabankalan destinations. No files changed.')
        return
    if '--dry-run' in sys.argv:
        print('DRY RUN OK: Can safely update the Explore Places links and browsing view.')
        for path in changed:
            print('  ' + str(path.relative_to(ROOT)) + ': ' + notes[path])
        print('No database, migrations, hobbies, map keys, or destination records will be changed.')
        return
    backup_dir = ROOT / 'phase4_backups' / ('explore-places-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup_dir.mkdir(parents=True, exist_ok=False)
    for path in changed:
        saved = backup_dir / path.relative_to(ROOT)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, saved)
    written = []
    try:
        for path in changed:
            if path.read_bytes() != original[path]:
                raise RuntimeError('File changed while installer was running: ' + str(path))
            path.write_bytes(planned[path])
            written.append(path)
    except Exception:
        for path in written:
            shutil.copy2(backup_dir / path.relative_to(ROOT), path)
        raise
    print('SUCCESS: Explore Places now opens all published Kabankalan destinations directly.')
    print('Updated:', ', '.join(str(p.relative_to(ROOT)) for p in changed))
    print('Backup:', backup_dir.relative_to(ROOT))
    print('Hobbies link and personalized search remain separate and unchanged.')
    print('No database, migrations, place records or MapTiler key changed.')
    print('Next: python manage.py check')
    print('Next: Visit /places/?browse=all from the Explore Places navbar link.')


if __name__ == '__main__':
    main()
