#!/usr/bin/env python3
"""Backup-safe ExploreAnywhere Phase 5D.3 Admin polish (presentation only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parent
TARGETS = json.loads((PACKAGE / 'manifest.json').read_text(encoding='utf-8'))['targets']


def sha(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def unix(data: bytes) -> bytes:
    return data.replace(b'\r\n', b'\n')


def known(data: bytes | None, expected: str) -> bool:
    return data is not None and sha(unix(data)) == expected


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix='.ea-phase5d3-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def project_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/admin.py').is_file():
        raise RuntimeError('Please run this script inside ExploreAnywhere, where manage.py is located.')
    return root


def package_output(relative: str, original: bytes) -> bytes:
    payload = read(PACKAGE / 'payload' / relative)
    if not known(payload, TARGETS[relative]['after']):
        raise RuntimeError('ZIP package file is missing or corrupted: ' + relative)
    return payload.replace(b'\n', b'\r\n') if b'\r\n' in original else payload


def status(root: Path) -> str:
    entries = {}
    for relative, hashes in TARGETS.items():
        content = read(root / relative)
        if known(content, hashes['before']):
            entries[relative] = 'before'
        elif known(content, hashes['after']):
            entries[relative] = 'installed'
        else:
            entries[relative] = 'changed'
    if 'changed' in entries.values():
        raise RuntimeError('Source differs from Phase 5D.2, so nothing was changed. Files: ' +
                           ', '.join(k for k, v in entries.items() if v == 'changed') +
                           '. Please upload the latest files for a custom patch.')
    if len(set(entries.values())) != 1:
        raise RuntimeError('Partial install detected; no changes made: ' + str(entries))
    return next(iter(entries.values()))


def validate(root: Path) -> None:
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    calls = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.template.loader import get_template; "
         "get_template('admin/base_site.html'); "
         "get_template('admin/places/place/change_list.html'); "
         "get_template('admin/index.html'); "
         "print('PASS: Admin templates compile, including native change-list object tools')"],
    ]
    for cmd in calls:
        print('VALIDATING: ' + ' '.join(cmd[1:]), flush=True)
        run = subprocess.run(cmd, cwd=root, env=env, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=120)
        print(run.stdout.strip(), flush=True)
        if run.returncode != 0:
            raise RuntimeError('Django verification failed (exit {}). Restoring.'.format(run.returncode))


def revert(root: Path, originals: dict[str, bytes]) -> None:
    for rel, content in originals.items():
        atomic_write(root / rel, content)


def restore(root: Path, backup_name: str) -> None:
    allowed = (root / 'phase5_backups').resolve()
    chosen = (root / backup_name).resolve()
    if not chosen.is_relative_to(allowed):
        raise RuntimeError('Restore path must be inside phase5_backups.')
    meta_file = chosen / 'backup_manifest.json'
    if not meta_file.is_file():
        raise RuntimeError('No valid backup manifest found at the specified location.')
    meta = json.loads(meta_file.read_text(encoding='utf-8'))
    if set(meta) != set(TARGETS):
        raise RuntimeError('Backup files do not match Phase 5D.3 targets.')
    originals = {}
    for rel, record in meta.items():
        data = read(chosen / 'original' / rel)
        if sha(data) != record.get('original_sha'):
            raise RuntimeError('Backup integrity verification failed: ' + rel)
        if sha(read(root / rel)) != record.get('installed_sha'):
            raise RuntimeError('File was changed since installation; restore stopped: ' + rel)
        originals[rel] = data
    revert(root, originals)
    print('RESTORED: Original files from', chosen)
    print('Database, models, and permissions were untouched.')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--restore', metavar='BACKUP_PATH')
    args = ap.parse_args()
    root = project_root()
    if args.restore:
        restore(root, args.restore)
        return
    current = status(root)
    if current == 'installed':
        print('ALREADY INSTALLED: Phase 5D.3 Admin UI is present.')
        if not args.dry_run:
            validate(root)
        return
    originals = {rel: read(root / rel) for rel in TARGETS}
    proposed = {rel: package_output(rel, content) for rel, content in originals.items()}
    if args.dry_run:
        print('DRY RUN OK: Phase 5D.2 Admin templates match this polish package.')
        print('Changes: active sidebar highlighting, permission-aware Add Place button positioning, compact header.')
        print('Updates ONLY: ' + ', '.join(TARGETS))
        print('Preserved: Django permission checks, admin actions, filters, data, migrations, and model code.')
        return
    backup = root / 'phase5_backups' / ('admin-final-polish-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    metadata = {}
    for rel, data in originals.items():
        original_file = backup / 'original' / rel
        original_file.parent.mkdir(parents=True, exist_ok=True)
        original_file.write_bytes(data)
        metadata[rel] = {'original_sha': sha(data), 'installed_sha': sha(proposed[rel])}
    (backup / 'backup_manifest.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('BACKUP:', backup.relative_to(root), flush=True)
    try:
        for rel, data in proposed.items():
            atomic_write(root / rel, data)
        validate(root)
    except Exception:
        revert(root, originals)
        print('ROLLBACK COMPLETE: Original admin templates restored.', flush=True)
        raise
    print('SUCCESS: Phase 5D.3 Admin final polish installed.')
    print('Updated only two Admin templates; no data or permission changes.')
    print('To restore: python "{}" --restore "{}"'.format(Path(__file__).resolve(), backup.relative_to(root)))
    print('NEXT: Restart Django; test /admin/ and /admin/places/place/.')


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        print('ERROR:', err, file=sys.stderr)
        sys.exit(1)
