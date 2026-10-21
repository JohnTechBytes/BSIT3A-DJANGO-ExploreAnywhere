#!/usr/bin/env python3
"""Backup-safe ExploreAnywhere Phase 6B.3: Nominatim boundary + category-sized queries.

From the ExploreAnywhere project root:
  python exploreanywhere_phase6b3_importer_repair.py --dry-run
  python exploreanywhere_phase6b3_importer_repair.py
  python exploreanywhere_phase6b3_importer_repair.py --restore phase6_backups/<folder>

Never makes network calls or modifies the Django database during installation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

TARGET = Path('apps/places/management/commands/discover_kabankalan_businesses.py')
BACKUPS = Path('phase6_backups')
FORMAT = 'exploreanywhere-phase6b3-business-importer-v1'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(data: bytes) -> bytes:
    return data.replace(b'\r\n', b'\n')


def is_inside(file: Path, folder: Path) -> bool:
    try:
        file.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + '.phase6b3.tmp')
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    a = parser.parse_args()
    root = Path.cwd().resolve()
    target = root / TARGET
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise SystemExit('ERROR: Run from the ExploreAnywhere folder containing manage.py.')
    if not target.is_file() or target.is_symlink() or not is_inside(target, root):
        raise SystemExit('ERROR: Phase 6B discovery command is missing or unsafe. No changes.')

    if a.restore:
        backup = Path(a.restore).expanduser()
        if not backup.is_absolute():
            backup = root / backup
        backup = backup.resolve()
        if not is_inside(backup, root / BACKUPS):
            raise SystemExit('ERROR: Restore folder must be inside phase6_backups.')
        meta = backup / 'manifest.json'
        orig = backup / 'original_discover_kabankalan_businesses.py'
        if not meta.is_file() or not orig.is_file():
            raise SystemExit('ERROR: Backup files are missing.')
        manifest = json.loads(meta.read_text(encoding='utf-8'))
        if manifest.get('format') != FORMAT or manifest.get('target') != TARGET.as_posix():
            raise SystemExit('ERROR: Backup does not belong to this patch.')
        data = orig.read_bytes()
        if sha(data) != manifest.get('before_sha256'):
            raise SystemExit('ERROR: Backup integrity check failed.')
        if sha(target.read_bytes()) != manifest.get('after_sha256'):
            raise SystemExit('ERROR: Importer has changed since installation; refusing to overwrite edits.')
        atomic_write(target, data)
        print('RESTORED: Original command restored. No database records changed.')
        return

    payload = Path(__file__).resolve().parent / 'payload'
    original = payload / 'original.py'
    upgraded = payload / 'updated.py'
    if not original.is_file() or not upgraded.is_file():
        raise SystemExit('ERROR: Installer payload missing. Extract the entire ZIP.')
    before = original.read_bytes()
    after = upgraded.read_bytes()
    try:
        compile(after.decode('utf-8'), str(TARGET), 'exec')
    except (SyntaxError, UnicodeError) as e:
        raise SystemExit(f'ERROR: Installer source invalid: {e}') from e
    current = target.read_bytes()
    if norm(current) == after:
        print('ALREADY INSTALLED: Phase 6B.3 importer repair matches expected source.')
        print('NEXT: python manage.py discover_kabankalan_businesses --boundary-only')
        return
    if norm(current) != before:
        raise SystemExit('ERROR: Current importer is different from reviewed Phase 6B.2 version. Nothing changed. Upload the current command for a tailored repair.')
    newline = b'\r\n' if b'\r\n' in current else b'\n'
    patched = after.replace(b'\n', newline)
    if a.dry_run:
        print('DRY RUN OK: Phase 6B.2 importer matches reviewed source.')
        print('Changes only:', TARGET.as_posix())
        print('Adds Nominatim city boundary resolution, --category smaller requests.')
        print('No DB, model, migration, map or published destination changes.')
        return

    backup = root / BACKUPS / ('osm-safe-importer-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    (backup / 'original_discover_kabankalan_businesses.py').write_bytes(current)
    (backup / 'manifest.json').write_text(json.dumps({
        'format': FORMAT,
        'target': TARGET.as_posix(),
        'before_sha256': sha(current),
        'after_sha256': sha(patched),
    }, indent=2), encoding='utf-8')
    try:
        atomic_write(target, patched)
        for args, expected in ((['check'], 'System check identified no issues'),
                               (['help', 'discover_kabankalan_businesses'], '--boundary-source')):
            result = subprocess.run([sys.executable, 'manage.py', *args], cwd=root,
                                    capture_output=True, text=True, timeout=90)
            if result.returncode or expected not in result.stdout:
                raise RuntimeError(f'Django {" ".join(args)} validation failed:\n{result.stdout}\n{result.stderr}')
        print('SUCCESS: Phase 6B.3 importer connection/query repair installed.')
        print('Backup:', backup.relative_to(root))
        print('FIRST TEST: python manage.py discover_kabankalan_businesses --boundary-only')
        print('THEN (if boundary works): python manage.py discover_kabankalan_businesses --category coffee')
        print('RESTORE: python', str(Path(__file__).resolve()), '--restore', str(backup.relative_to(root)))
        print('No network request or DB change was made during installation.')
    except Exception as e:
        if target.exists() and sha(target.read_bytes()) == sha(patched):
            atomic_write(target, current)
            print('AUTOMATIC ROLLBACK: Previous importer restored.')
        print('INSTALL VALIDATION FAILED:', e)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
