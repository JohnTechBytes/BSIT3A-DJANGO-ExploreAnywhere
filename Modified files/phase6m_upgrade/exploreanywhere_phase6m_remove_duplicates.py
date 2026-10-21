#!/usr/bin/env python3
"""Phase 6M: remove duplicated Discover navigation on ExploreAnywhere.
Only two templates change; no database or model changes.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

FILES = (
    'templates/places/_discovery_modes.html',
    'templates/places/nearby_places.html',
)
MANIFEST = 'PHASE6M_MANIFEST.json'


def root_dir() -> Path:
    here = Path.cwd()
    if not (here / 'manage.py').is_file():
        raise RuntimeError('Open the ExploreAnywhere project folder containing manage.py, then retry.')
    return here


def replace_one(data: str, old: str, new: str, where: str) -> str:
    count = data.count(old)
    if count != 1:
        raise RuntimeError(f'{where}: expected one matching source block, found {count}; not changing files. Upload your current templates if they were edited.')
    return data.replace(old, new, 1)


def change(name: str, current: bytes) -> bytes:
    bom = b'\xef\xbb\xbf'
    is_bom = current.startswith(bom)
    crlf = b'\r\n' in current
    src = current.decode('utf-8-sig').replace('\r\n', '\n')
    if name == FILES[0]:
        # Keep all three tab links and their active modes; remove only the redundant
        # explanation and category shortcut row (which duplicates Nearby quick search).
        src = replace_one(src,
            '  <p class="ea6f-explain">Explore verified Kabankalan places. Search for an interest, browse nearby listings, or switch to the map.</p>\n',
            '', name)
        opening = '  {% if active_discovery_mode != "nearby" %}\n  <div class="ea6f-categories" aria-label="Find a type of place">'
        closing = '  </div>\n  {% endif %}\n</nav>'
        if src.count(opening) != 1 or src.count(closing) != 1:
            raise RuntimeError(name + ': the category shortcut structure has changed; no files modified.')
        left = src.index(opening)
        right = src.index(closing, left) + len('  </div>\n  {% endif %}\n')
        chunk = src[left:right]
        if chunk.count('Popular searches:') != 1 or chunk.count('service=') != 5:
            raise RuntimeError(name + ': category links differ from expected; no files modified.')
        src = src[:left] + src[right:]
        # Remove now-unused styles for the removed explanatory row and category links.
        lines = src.splitlines(keepends=True)
        lines = [line for line in lines if not line.startswith(('.ea6f-explain{', '.ea6f-categories{', '.ea6f-categories span{', '.ea6f-categories a{', '.ea6f-categories a:hover', '.ea6f-categories a[aria-current'))]
        src = ''.join(lines)
        src = replace_one(src,'.ea6f-tab:focus-visible,.ea6f-categories a:focus-visible{', '.ea6f-tab:focus-visible{', name)
        src = replace_one(src,'.ea6f-nav{margin:0 0 20px;background:#fff;border:1px solid #dce6f3;border-radius:17px;padding:14px 16px;', '.ea6f-nav{margin:0 0 20px;background:#fff;border:1px solid #dce6f3;border-radius:17px;padding:12px 16px;', name)
    elif name == FILES[1]:
        src = replace_one(src,
            '    <a class="ea6-back" href="{% url \'places:attraction_carousel\' %}?browse=all">← All Places</a>\n',
            '', name)
        if src.count('<div class="ea6-quick"') != 1:
            raise RuntimeError(name + ': missing Nearby quick searches, no changes made.')
    else:
        raise RuntimeError('Unexpected target template: ' + name)
    dest = src.replace('\n', '\r\n') if crlf else src
    return (bom if is_bom else b'') + dest.encode('utf-8')


def backup_originals(root: Path, original: dict[str, bytes]) -> Path:
    folder = root / 'phase6_backups'
    folder.mkdir(exist_ok=True)
    backup = folder / ('phase6m_navigation_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.zip')
    manifest = {'phase': '6M', 'files': {k: sha256(v).hexdigest() for k, v in original.items()}}
    with ZipFile(backup, 'x', ZIP_DEFLATED) as archive:
        for filename, data in original.items():
            archive.writestr(filename, data)
        archive.writestr(MANIFEST, json.dumps(manifest, indent=2))
    return backup


def restore(root: Path, backup: Path) -> None:
    with ZipFile(backup) as archive:
        manifest = json.loads(archive.read(MANIFEST))
        originals = {name: archive.read(name) for name in FILES}
        for name, data in originals.items():
            if manifest.get('files', {}).get(name) != sha256(data).hexdigest():
                raise RuntimeError('Backup checksum mismatch: '+name)
    for name in FILES:
        if not (root / name).is_file():
            raise RuntimeError('Project template is missing: ' + name)
    for name, data in originals.items():
        (root / name).write_bytes(data)
    print('RESTORE OK: restored both source templates from', backup)


def validate_django(root: Path) -> None:
    checks = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         'from django.template.loader import get_template; '
         '[get_template(n) for n in ' + repr(list(FILES)) + ']; '
         'print("TEMPLATE CHECK OK: 2 templates compiled")'],
    ]
    for command in checks:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
        if result.stdout.strip(): print(result.stdout.strip())
        if result.returncode:
            raise RuntimeError('Django validation failed: ' + (result.stderr or result.stdout)[-1800:])


def main() -> int:
    parser = argparse.ArgumentParser(description='Phase 6M: Remove redundant Nearby UI sections')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_ZIP')
    options = parser.parse_args()
    try:
        root = root_dir()
        if options.restore:
            restore(root, Path(options.restore).expanduser().resolve())
            return 0
        existing = {}
        changed = {}
        for name in FILES:
            path = root / name
            if not path.is_file():
                raise RuntimeError('Missing required template: ' + name)
            existing[name] = path.read_bytes()
            changed[name] = change(name, existing[name])
        if options.dry_run:
            print('DRY RUN OK: both Phase 6L templates are compatible. Nothing changed.')
            for filename in FILES:
                print('  READY:', filename)
            return 0
        backup = backup_originals(root, existing)
        print('BACKUP:', backup)
        try:
            for name, data in changed.items():
                (root / name).write_bytes(data)
            validate_django(root)
        except Exception:
            for name, data in existing.items():
                (root / name).write_bytes(data)
            print('ROLLBACK: original templates restored; backup retained.')
            raise
        print('INSTALL OK: removed duplicate popular searches, nav explanation and redundant All Places header link.')
        print('No database, recommendation, or MapTiler logic changed.')
        print('Restore if necessary: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup) + '"')
        return 0
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
