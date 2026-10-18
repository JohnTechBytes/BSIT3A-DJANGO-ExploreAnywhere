#!/usr/bin/env python3
"""Phase 5E.2: backup-safe mobile navigation and offscreen photo optimization."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

PACKAGE = Path(__file__).resolve().parent
MANIFEST = json.loads((PACKAGE / 'manifest.json').read_text(encoding='utf-8'))


def lf(raw: bytes) -> bytes:
    return raw.replace(b'\r\n', b'\n')


def digest(raw: bytes) -> str:
    return hashlib.sha256(lf(raw)).hexdigest()


def put_atomic(target: Path, raw: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.ea5e2-', dir=str(target.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def check_root(root: Path) -> None:
    if not (root / 'manage.py').is_file():
        raise RuntimeError('Run from the ExploreAnywhere project root (manage.py not found).')


def validate_django(root: Path) -> None:
    cmds = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.template.loader import get_template; "
         "[get_template(name) for name in "
         "['theme/public_base.html','places/saved_places.html','places/place_detail.html']]; "
         "print('PASS: Phase 5E.2 templates compile')"],
    ]
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root) + os.pathsep + env.get('PYTHONPATH', '')
    for cmd in cmds:
        print('VALIDATING:', ' '.join(cmd[1:]), flush=True)
        result = subprocess.run(cmd, cwd=str(root), env=env, check=False)
        if result.returncode:
            raise RuntimeError(f'Django validation exited with code {result.returncode}')


def restore(root: Path, folder_arg: str) -> None:
    backup_root = (root/'phase5_backups').resolve()
    folder = (root/folder_arg).resolve()
    if not folder.is_relative_to(backup_root):
        raise RuntimeError('Restore path must be inside phase5_backups.')
    info = json.loads((folder/'backup.json').read_text(encoding='utf-8'))
    if info.get('phase') != '5E.2':
        raise RuntimeError('Not a Phase 5E.2 backup.')
    # Verify every file before writing anything, to prevent clobbering newer changes.
    for rel, recorded in info['files'].items():
        target = root/rel
        if not target.is_file() or digest(target.read_bytes()) != recorded['installed_sha256']:
            raise RuntimeError(f'Restore refused: {rel} has changed since this installation.')
        if hashlib.sha256((folder/rel).read_bytes()).hexdigest() != recorded['original_sha256']:
            raise RuntimeError(f'Restore refused: backup content mismatch in {rel}.')
    for rel in info['files']:
        put_atomic(root/rel, (folder/rel).read_bytes())
    print('RESTORED: Exact original template files from', folder)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    check_root(root)
    if args.restore:
        restore(root, args.restore)
        return 0

    updates = {}
    for rel, hashes in MANIFEST.items():
        target = root/rel
        if not target.is_file():
            raise RuntimeError(f'Cannot find required template: {rel}')
        original = target.read_bytes()
        current = digest(original)
        if current == hashes['new']:
            continue
        if current != hashes['old']:
            raise RuntimeError(f'Compatibility mismatch in {rel}. Nothing changed. Upload your latest source for an updated installer.')
        update = (PACKAGE/'payload'/rel).read_bytes()
        if digest(update) != hashes['new']:
            raise RuntimeError(f'Package payload failed integrity check: {rel}')
        # Mirror original newline style. Byte-for-byte original copies are stored separately.
        if b'\r\n' in original:
            update = update.replace(b'\n', b'\r\n')
        updates[rel] = (original, update)

    if args.dry_run:
        print('DRY RUN OK: Phase 5E.2 mobile/navigation source is compatible.')
        print('Would update:', ', '.join(updates) if updates else 'nothing (already installed)')
        print('Preserved: maps, Kabankalan filtering, recommendations, saved/visit actions, Admin, DB.')
        return 0
    if not updates:
        print('ALREADY INSTALLED: Phase 5E.2 files match the expected upgrade.')
        validate_django(root)
        return 0

    backup = root/'phase5_backups'/('mobile-images-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if backup.exists():
        raise RuntimeError('Backup directory already exists; stopping safely.')
    for rel, (original, _update) in updates.items():
        dest = backup/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(original)
    info = {
        'phase': '5E.2',
        'files': {rel: {
            'original_sha256': hashlib.sha256(original).hexdigest(),
            'installed_sha256': digest(update),
        } for rel, (original, update) in updates.items()},
    }
    (backup/'backup.json').write_text(json.dumps(info, indent=2)+'\n',encoding='utf-8')
    print('BACKUP:', backup.relative_to(root), flush=True)
    try:
        for rel, (_, update) in updates.items():
            put_atomic(root/rel, update)
        validate_django(root)
    except BaseException:
        for rel, (original, _update) in updates.items():
            put_atomic(root/rel, original)
        print('INSTALL VALIDATION FAILED: exact originals restored from', backup, flush=True)
        raise
    print('SUCCESS: ExploreAnywhere Phase 5E.2 installed.')
    print('Updated only:', ', '.join(updates))
    print('To restore: python "'+str(Path(__file__).resolve())+'" --restore "'+str(backup.relative_to(root))+'"')
    print('NEXT: restart Django; test mobile menu, Saved Places, and photo gallery.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        raise SystemExit(1)
