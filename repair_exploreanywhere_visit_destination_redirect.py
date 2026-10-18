#!/usr/bin/env python3
"""Phase 4F: allow directly opening published Kabankalan place details from My Visits.

Run from the Django project root. Backs up the existing apps/places/views.py.
Supports --dry-run. Does not alter auth requirements, city filters, or database.
"""
import ast
import datetime
import pathlib
import shutil
import sys

ROOT = pathlib.Path.cwd()
TARGET = ROOT / 'apps' / 'places' / 'views.py'
MARKER = '# phase4f: place details accessible without hobby-selection session'


def fail(message):
    raise SystemExit('STOPPED: ' + message + ' No files changed.')


def is_hobby_redirect(node, source):
    if not isinstance(node, ast.If):
        return False
    test_text = ast.get_source_segment(source, node.test) or ''
    if 'hobbies_city_id' not in test_text or 'selected_hobbies' not in test_text:
        return False
    if node.orelse or len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return False
    value = node.body[0].value
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'redirect'):
        return False
    return (len(value.args) == 1 and isinstance(value.args[0], ast.Constant)
            and value.args[0].value == 'hobbies:select')


def main():
    if not (ROOT / 'manage.py').is_file() or not TARGET.is_file():
        fail('Please run from the ExploreAnywhere project root (where manage.py is).')
    original_bytes = TARGET.read_bytes()
    has_bom = original_bytes.startswith(b'\xef\xbb\xbf')
    try:
        source = original_bytes.decode('utf-8-sig')
        tree = ast.parse(source, filename=str(TARGET))
    except (UnicodeDecodeError, SyntaxError) as exc:
        fail(f'Cannot safely read/parse views.py: {exc}')
    defs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == 'place_detail']
    if len(defs) != 1:
        fail(f'Expected exactly one place_detail view, found {len(defs)}.')
    view = defs[0]
    if MARKER in source:
        print('ALREADY FIXED: Place Details no longer requires hobby selection. No files changed.')
        return
    matches = [node for node in view.body if is_hobby_redirect(node, source)]
    if len(matches) != 1:
        fail('Could not find the exact hobby-session redirect inside place_detail; project differs from reviewed code.')
    block = matches[0]
    # Require login and published Kabankalan destination checks remain intact.
    decorators = '\n'.join(ast.get_source_segment(source, decorator) or '' for decorator in view.decorator_list)
    if 'login_required' not in decorators:
        fail('Place Details has no known login_required decorator; manual review required.')
    function_text = ast.get_source_segment(source, view) or ''
    for required in ('get_object_or_404', 'is_active=True', 'is_verified=True', 'city=city'):
        if required not in function_text:
            fail(f'Place Details missing expected published-city guard {required!r}; manual review required.')
    lines = source.splitlines(keepends=True)
    start, end = block.lineno - 1, block.end_lineno
    if not (0 <= start < end <= len(lines)):
        fail('Line boundaries not valid.')
    newline = '\r\n' if b'\r\n' in original_bytes else '\n'
    lines[start:end] = ['    ' + MARKER + newline,
                        '    # Saved Places, reviews and visit history must open details directly.' + newline]
    updated = ''.join(lines)
    try:
        ast.parse(updated, filename=str(TARGET))
        compile(updated, str(TARGET), 'exec')
    except SyntaxError as exc:
        fail(f'Patched file would not compile: {exc}')
    if '--dry-run' in sys.argv:
        print('DRY RUN OK: Can remove only the hobby-selection redirect from place_detail.')
        print('Preserves: login_required, published Kabankalan place filter, discovery flow, all URLs and database.')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_dir = ROOT / 'phase4_backups' / ('visit-detail-link-' + stamp)
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup = backup_dir / 'views.py'
    shutil.copy2(TARGET, backup)
    try:
        patched_bytes = updated.encode('utf-8')
        if has_bom:
            patched_bytes = b'\xef\xbb\xbf' + patched_bytes
        TARGET.write_bytes(patched_bytes)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise
    print('SUCCESS: My Visits -> View Destination now opens Place Details directly.')
    print('Modified ONLY: apps/places/views.py')
    print('Backup:', backup.relative_to(ROOT))
    print('Preserved: authentication, Kabankalan-only published-place checks, hobby discovery, database and maps.')
    print('Next: python manage.py check')
    print('Next: open /visits/ and click View Destination again.')


if __name__ == '__main__':
    main()
