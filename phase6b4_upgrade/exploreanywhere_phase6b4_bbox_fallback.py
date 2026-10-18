#!/usr/bin/env python3
"""Backup-safe Phase 6B.4 Overpass bounded-query fallback for ExploreAnywhere.

Run from the ExploreAnywhere project directory:
  python .\phase6b4_upgrade\exploreanywhere_phase6b4_bbox_fallback.py --dry-run
  python .\phase6b4_upgrade\exploreanywhere_phase6b4_bbox_fallback.py
  python .\phase6b4_upgrade\exploreanywhere_phase6b4_bbox_fallback.py --restore phase6_backups\<backup>

No network requests or database modifications during installation.
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
FORMAT = 'exploreanywhere-phase6b4-bbox-fallback-v1'

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def norm(data: bytes) -> bytes:
    return data.replace(b'\r\n', b'\n')

def within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False

def atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + '.phase6b4.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--restore', metavar='BACKUP_FOLDER')
    args = ap.parse_args()
    root = Path.cwd().resolve()
    target = root / TARGET
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise SystemExit('ERROR: Run from the ExploreAnywhere folder containing manage.py.')
    if not target.is_file() or target.is_symlink() or not within(target,root):
        raise SystemExit('ERROR: The Phase 6B importer is missing or unsafe. Nothing changed.')

    if args.restore:
        folder = Path(args.restore).expanduser()
        if not folder.is_absolute(): folder = root / folder
        folder = folder.resolve()
        if not within(folder, root / BACKUPS):
            raise SystemExit('ERROR: Backup must be within phase6_backups.')
        manifest_file = folder / 'manifest.json'
        backup = folder / 'original_discover_kabankalan_businesses.py'
        if not manifest_file.is_file() or not backup.is_file():
            raise SystemExit('ERROR: Backup manifest or source missing.')
        m = json.loads(manifest_file.read_text(encoding='utf-8'))
        if m.get('format') != FORMAT or m.get('target') != TARGET.as_posix():
            raise SystemExit('ERROR: Backup does not belong to this patch.')
        saved = backup.read_bytes()
        if sha(saved) != m.get('before_sha256'):
            raise SystemExit('ERROR: Original backup checksum differs from manifest.')
        if sha(target.read_bytes()) != m.get('after_sha256'):
            raise SystemExit('ERROR: Importer changed since installation; not overwriting new edits.')
        atomic_write(target, saved)
        print('RESTORED: Prior importer recovered without database changes.')
        return

    payload = Path(__file__).resolve().parent / 'payload'
    original, patched_file = payload / 'original.py', payload / 'updated.py'
    if not original.is_file() or not patched_file.is_file():
        raise SystemExit('ERROR: Installer payload missing; extract the whole ZIP.')
    before, after = original.read_bytes(), patched_file.read_bytes()
    compile(after.decode('utf-8'), str(TARGET), 'exec')
    current = target.read_bytes()
    if norm(current) == after:
        print('ALREADY INSTALLED: Phase 6B.4 bounded-query fallback matches this package.')
        print('NEXT: python manage.py discover_kabankalan_businesses --query-mode bbox --probe-bbox')
        return
    if norm(current) != before:
        raise SystemExit('ERROR: Installed importer differs from the reviewed Phase 6B.3 source. No changes made. Upload your current importer for a tailored patch.')
    newline = b'\r\n' if b'\r\n' in current else b'\n'
    target_bytes = after.replace(b'\n', newline)
    if args.dry_run:
        print('DRY RUN OK: Phase 6B.3 importer matches the reviewed source.')
        print('Will update ONLY:', TARGET.as_posix())
        print('Adds --query-mode bbox and --probe-bbox with Nominatim polygon check.')
        print('Preserves normal area query, imports, Django models, database, map and publication rules.')
        return

    folder = root / BACKUPS / ('osm-bbox-fallback-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'original_discover_kabankalan_businesses.py').write_bytes(current)
    (folder / 'manifest.json').write_text(json.dumps({
        'format': FORMAT, 'target': TARGET.as_posix(),
        'before_sha256': sha(current), 'after_sha256': sha(target_bytes),
    }, indent=2), encoding='utf-8')
    try:
        atomic_write(target, target_bytes)
        for options, needed in (
            (['check'], 'System check identified no issues'),
            (['help','discover_kabankalan_businesses'], '--query-mode'),
        ):
            result = subprocess.run([sys.executable, 'manage.py', *options], cwd=root,
                                    capture_output=True, text=True, timeout=90)
            if result.returncode or needed not in result.stdout:
                raise RuntimeError('Django ' + ' '.join(options) + ' failed:\n' + result.stdout + '\n' + result.stderr)
        print('SUCCESS: Phase 6B.4 optional bbox fallback installed; Django checks passed.')
        print('Backup:', folder.relative_to(root))
        print('FIRST TEST: python manage.py discover_kabankalan_businesses --query-mode bbox --probe-bbox')
        print('IF SUCCESSFUL: python manage.py discover_kabankalan_businesses --query-mode bbox --category coffee')
        print('RESTORE: python', str(Path(__file__).resolve()), '--restore', str(folder.relative_to(root)))
        print('No Overpass request, database rows, migrations or existing records changed during installation.')
    except Exception as err:
        if target.is_file() and sha(target.read_bytes()) == sha(target_bytes):
            atomic_write(target, current)
            print('AUTOMATIC ROLLBACK: Original importer restored.')
        raise SystemExit('INSTALL VALIDATION FAILED: ' + str(err))

if __name__ == '__main__':
    main()
