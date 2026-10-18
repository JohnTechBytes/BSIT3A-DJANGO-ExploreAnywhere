#!/usr/bin/env python3
"""Backup-safe Phase 6B.2: narrow Overpass boundary discovery, clearer failures.

Run from the ExploreAnywhere folder containing manage.py. Does not contact the
internet or write any DB rows. The installed Django command performs network
requests only when invoked explicitly by the user.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

TARGET = Path('apps/places/management/commands/discover_kabankalan_businesses.py')
ROOT_BACKUPS = Path('phase6_backups')
FMT = 'exploreanywhere-phase6b2-query-fix-v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(data):
    return data.replace(b'\r\n', b'\n')


def under(path, folder):
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def atomic_write(path, content):
    temporary = path.with_name(path.name + '.phase6b2.tmp')
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise SystemExit('ERROR: Run from ExploreAnywhere project root containing manage.py.')
    target = root / TARGET
    if not target.is_file() or target.is_symlink() or not under(target, root):
        raise SystemExit('ERROR: Phase 6B management command missing or unsafe. Nothing changed.')

    if args.restore:
        backup = Path(args.restore).expanduser()
        if not backup.is_absolute():
            backup = root / backup
        backup = backup.resolve()
        if not under(backup, root / ROOT_BACKUPS):
            raise SystemExit('ERROR: Restore folder must be inside phase6_backups.')
        manifest_file = backup / 'manifest.json'
        original_file = backup / 'original_discover_kabankalan_businesses.py'
        if not (manifest_file.is_file() and original_file.is_file()):
            raise SystemExit('ERROR: Missing restoration files.')
        manifest = json.loads(manifest_file.read_text(encoding='utf8'))
        if manifest.get('format') != FMT or manifest.get('target') != TARGET.as_posix():
            raise SystemExit('ERROR: Backup does not belong to this update.')
        old_content = original_file.read_bytes()
        if sha(old_content) != manifest.get('old_sha256'):
            raise SystemExit('ERROR: Original backup checksum differs; refusing restore.')
        if sha(target.read_bytes()) != manifest.get('new_sha256'):
            raise SystemExit('ERROR: Source changed since installation; refusing to overwrite it.')
        atomic_write(target, old_content)
        print('RESTORED: Original Phase 6B command restored; database unchanged.')
        return

    payload = Path(__file__).resolve().parent / 'payload'
    old_file = payload / 'original.py'
    new_file = payload / 'updated.py'
    if not old_file.is_file() or not new_file.is_file():
        raise SystemExit('ERROR: Installer payload is missing. Extract the entire ZIP first.')
    old_expected = old_file.read_bytes()
    new_expected = new_file.read_bytes()
    try:
        compile(new_expected.decode('utf8'), str(TARGET), 'exec')
    except (UnicodeError, SyntaxError) as exc:
        raise SystemExit(f'ERROR: Invalid installer payload: {exc}')
    current = target.read_bytes()
    if normalize(current) == new_expected:
        print('ALREADY INSTALLED: Phase 6B.2 lightweight lookup is present.')
        print('NEXT: python manage.py discover_kabankalan_businesses --boundary-only')
        return
    if normalize(current) != old_expected:
        raise SystemExit('ERROR: Current importer differs from the reviewed Phase 6B endpoint fix. No changes made. Please upload this command source for a tailored fix.')
    line_ending = b'\r\n' if b'\r\n' in current else b'\n'
    patched = new_expected.replace(b'\n', line_ending)
    if args.dry_run:
        print('DRY RUN OK: Phase 6B endpoint-fixed importer matches reviewed source.')
        print('Will update ONLY:', TARGET.as_posix())
        print('Improves: exact-name boundary query, --boundary-only, stage-specific errors.')
        print('Preserves: import safety, existing verified places, OSM attribution, DB, migrations.')
        print('No network request or database write in the installer.')
        return

    backup = root / ROOT_BACKUPS / ('osm-light-query-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    (backup / 'original_discover_kabankalan_businesses.py').write_bytes(current)
    (backup / 'manifest.json').write_text(json.dumps({
        'format': FMT,
        'target': TARGET.as_posix(),
        'old_sha256': sha(current),
        'new_sha256': sha(patched),
    }, indent=2), encoding='utf8')
    try:
        atomic_write(target, patched)
        for cmd in (['check'], ['help', 'discover_kabankalan_businesses']):
            result = subprocess.run([sys.executable, 'manage.py', *cmd], cwd=root,
                                    capture_output=True, text=True, timeout=100)
            if result.returncode:
                raise RuntimeError(f'Django {" ".join(cmd)} failed:\n{result.stdout}\n{result.stderr}')
            if cmd[0] == 'help' and '--boundary-only' not in result.stdout:
                raise RuntimeError('Django did not register --boundary-only flag.')
        print('SUCCESS: Phase 6B.2 lightweight Overpass boundary lookup installed.')
        print('Backup:', backup.relative_to(root))
        print('FIRST TEST: python manage.py discover_kabankalan_businesses --boundary-only')
        print('RESTORE: python', str(Path(__file__).resolve()), '--restore', str(backup.relative_to(root)))
        print('No database rows or migrations changed; no Overpass request made by installer.')
    except Exception as exc:
        if target.is_file() and sha(target.read_bytes()) == sha(patched):
            atomic_write(target, current)
            print('ROLLED BACK: Original importer restored after validation failed.')
        print('INSTALL VALIDATION FAILED:', exc)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
