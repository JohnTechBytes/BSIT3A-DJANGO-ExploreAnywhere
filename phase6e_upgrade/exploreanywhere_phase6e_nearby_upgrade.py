#!/usr/bin/env python3
"""ExploreAnywhere Phase 6E: approved business suggestions and nearby search.

Run in the ExploreAnywhere folder. Use --dry-run before installing.
Only updates two existing Nearby Places files, never models or database rows.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

TARGETS = (
    'apps/places/nearby.py',
    'templates/places/nearby_places.html',
)
FORMAT = 'exploreanywhere-phase6e-nearby-v1'
EXPECTED = {
    'apps/places/nearby.py': '9ee3339020ba361569b8a3c98e92c12cf2dd58e7bdd2447cd11842189be33577',
    'templates/places/nearby_places.html': '1a33a7c5b34c8ccb8add8c0ca4f233655be1ffe3cafa64003756085054331b5b',
}


def checksum(data: bytes) -> str:
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def root_path() -> Path:
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise RuntimeError('Run this installer in the ExploreAnywhere project folder containing manage.py.')
    return root


def inspect(root: Path, package: Path):
    state = {}
    for name in TARGETS:
        dest = root / name
        source = package / 'payload' / name
        if not source.is_file() or not dest.is_file():
            raise RuntimeError('Required existing project file or package file is missing: ' + name)
        current = dest.read_bytes()
        new = source.read_bytes()
        if b'\r\n' in current and b'\r\n' not in new:
            new = new.replace(b'\n', b'\r\n')
        if checksum(current) == checksum(new):
            action = 'already installed'
        elif checksum(current) == EXPECTED[name]:
            action = 'update'
        else:
            raise RuntimeError('Unexpected modifications in ' + name + '. No files changed. Upload the latest files to build a compatible patch.')
        state[name] = (action, current, new)
    return state


def create_backup(root: Path, state):
    base = root / 'phase6_backups' / ('nearby-suggestions-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    base.mkdir(parents=True, exist_ok=False)
    manifest = {'format': FORMAT, 'files': []}
    for name, (action, existing, target) in state.items():
        if action != 'update':
            continue
        original = base / 'originals' / name
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(existing)
        manifest['files'].append({'path':name, 'installed_hash':checksum(target)})
    (base / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return base


def restore(root: Path, backup: Path):
    backup = backup.resolve()
    if not backup.is_relative_to((root / 'phase6_backups').resolve()):
        raise RuntimeError('Only backups within this project phase6_backups folder can be restored.')
    manifest_file = backup / 'manifest.json'
    if not manifest_file.is_file():
        raise RuntimeError('Backup manifest not found: ' + str(manifest_file))
    info = json.loads(manifest_file.read_text(encoding='utf-8'))
    if info.get('format') != FORMAT:
        raise RuntimeError('Incorrect backup format; stopping.')
    changes = []
    for entry in info['files']:
        name = entry['path']
        if name not in TARGETS:
            raise RuntimeError('Unsafe backup entry: ' + name)
        dest = root / name
        prev = (backup / 'originals' / name).read_bytes()
        if not dest.is_file():
            raise RuntimeError('Installed file missing; inspect before restoring: ' + name)
        current = dest.read_bytes()
        if checksum(current) not in {entry['installed_hash'], checksum(prev)}:
            raise RuntimeError('File was edited after installation; refusing overwrite: ' + name)
        changes.append((dest, prev))
    for dest, contents in changes:
        dest.write_bytes(contents)
    print('RESTORED original Nearby Places files from', backup)
    print('No records, migrations, settings or admin permissions were changed.')


def validate(root: Path):
    checks = (
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.template.loader import get_template; "
         "from django.urls import resolve; "
         "from apps.places.nearby import nearby_places, smart_search; "
         "from apps.places.nearby_intent import detect_service_intent; "
         "assert resolve('/places/nearby/').url_name == 'nearby_places'; "
         "assert detect_service_intent('where can i find a coffeshop near me') == 'coffee'; "
         "assert detect_service_intent('Coffee & Talk') == 'coffee'; "
         "get_template('places/nearby_places.html'); "
         "print('PASS: Nearby template, routes and coffee intent compiled')"],
    )
    for command in checks:
        print('VALIDATING:', ' '.join(command[1:3]), flush=True)
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=120)
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode:
            raise RuntimeError('Django validation failed (exit code ' + str(result.returncode) + ')')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    options = parser.parse_args()
    root = root_path()
    if options.restore:
        base = Path(options.restore)
        if not base.is_absolute():
            base = root / base
        restore(root, base)
        return
    state = inspect(root, Path(__file__).resolve().parent)
    changes = [name for name in TARGETS if state[name][0] == 'update']
    if not changes:
        print('ALREADY INSTALLED: Phase 6E nearby search already matches this package.')
        return
    print('READY: Phase 6E Smart Nearby Search & verified-place autocomplete.')
    print('Will modify ONLY:', ', '.join(changes))
    print('Preserved: verified/active city filtering, browser-only GPS, current map links, DB, migrations and admin checks.')
    if options.dry_run:
        print('DRY RUN OK: no files or database records changed.')
        return
    backup = create_backup(root, state)
    print('BACKUP:', backup.relative_to(root), flush=True)
    try:
        for name in changes:
            (root/name).write_bytes(state[name][2])
        validate(root)
    except Exception as exc:
        print('INSTALL VALIDATION FAILED:', exc, file=sys.stderr)
        restore(root, backup)
        raise RuntimeError('Automatically rolled back; review the error above.') from exc
    print('SUCCESS: Phase 6E approved nearby suggestions installed.')
    print('No database writes, migrations, settings, admin permissions, or external GPS requests.')
    print('RESTORE: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup.relative_to(root)) + '"')
    print('NEXT: Restart Django and test /places/nearby/ with Coffee & Talk and coffee shop near me.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('ERROR:', error, file=sys.stderr)
        sys.exit(1)
