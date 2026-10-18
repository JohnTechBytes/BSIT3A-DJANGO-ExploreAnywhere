#!/usr/bin/env python3
"""ExploreAnywhere Phase 5D.2: backup-safe, reversible Django Admin cleanup."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
TARGETS = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))['targets']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.ea-admin-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def root_project():
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/admin.py').is_file():
        raise RuntimeError('Open your ExploreAnywhere folder containing manage.py before running this installer.')
    return root


def state(root):
    statuses = {}
    for relative, sums in TARGETS.items():
        current = sha(root / relative)
        if current == sums['before']:
            statuses[relative] = 'original'
        elif current == sums['after']:
            statuses[relative] = 'installed'
        else:
            statuses[relative] = 'unexpected'
    if 'unexpected' in statuses.values():
        changed = [k for k, v in statuses.items() if v == 'unexpected']
        raise RuntimeError('Compatibility check stopped to protect changed source files: ' + ', '.join(changed))
    if len(set(statuses.values())) != 1:
        raise RuntimeError('Partial installation detected; no files changed. Current file states: ' + str(statuses))
    return next(iter(statuses.values()))


def validate(root):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    commands = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.template.loader import get_template; get_template('admin/places/place/change_list.html'); get_template('admin/index.html'); print('PASS: New admin templates compile')"],
    ]
    for command in commands:
        print('VALIDATING:', ' '.join(command[1:]), flush=True)
        proc = subprocess.run(command, cwd=root, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=120)
        print(proc.stdout.strip(), flush=True)
        if proc.returncode:
            raise RuntimeError(f'Validation exited with code {proc.returncode}. Changes will be rolled back.')


def restore_bytes(root, originals):
    for rel, content in originals.items():
        path = root / rel
        if content is None:
            path.unlink(missing_ok=True)
        else:
            write_atomic(path, content)


def restore_backup(root, name):
    base = (root / 'phase5_backups').resolve()
    backup = (root / name).resolve()
    if not backup.is_relative_to(base) or not (backup / 'backup_manifest.json').is_file():
        raise RuntimeError('Provide a valid Phase 5D.2 backup inside the project phase5_backups folder.')
    record = json.loads((backup / 'backup_manifest.json').read_text(encoding='utf8'))
    if set(record) != set(TARGETS):
        raise RuntimeError('Restore refused: backup target set is incomplete.')
    originals = {}
    for rel, meta in record.items():
        if meta['installed'] != TARGETS[rel]['after'] or sha(root / rel) != meta['installed']:
            raise RuntimeError('Restore refused: file was modified after installation: ' + rel)
        original = backup / 'original' / rel
        if meta['existed']:
            if sha(original) != meta['original']:
                raise RuntimeError('Backup integrity check failed for ' + rel)
            originals[rel] = original.read_bytes()
        else:
            if meta['original'] is not None:
                raise RuntimeError('Backup metadata invalid for ' + rel)
            originals[rel] = None
    restore_bytes(root, originals)
    print('RESTORED: Exact original admin files from', backup)
    print('No database, migrations, staff permissions, or records changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    args = parser.parse_args()
    root = root_project()
    if args.restore:
        restore_backup(root, args.restore)
        return
    for rel, hashes in TARGETS.items():
        if sha(HERE / 'payload' / rel) != hashes['after']:
            raise RuntimeError('Package missing/corrupt: ' + rel)
    current_state = state(root)
    if current_state == 'installed':
        print('ALREADY INSTALLED: All four Phase 5D.2 files match this package.')
        if not args.dry_run:
            validate(root)
        return
    if args.dry_run:
        print('DRY RUN OK: Compatible with your uploaded Phase 5D.2 admin source.')
        print('Updates: compact filters, concise table, better sidebar, cleaner dashboard.')
        print('Targets: ' + ', '.join(TARGETS))
        print('Preserved: staff permissions, photo rights, coordinate checks, approval actions, database and migrations.')
        return
    originals = {rel: (root / rel).read_bytes() if (root / rel).is_file() else None for rel in TARGETS}
    backup = root / 'phase5_backups' / ('destination-admin-cleanup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    record = {}
    for rel, content in originals.items():
        record[rel] = {'existed': content is not None, 'original': TARGETS[rel]['before'], 'installed': TARGETS[rel]['after']}
        if content is not None:
            original_path = backup / 'original' / rel
            original_path.parent.mkdir(parents=True, exist_ok=True)
            original_path.write_bytes(content)
    (backup / 'backup_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf8')
    print('BACKUP:', backup.relative_to(root), flush=True)
    try:
        for rel in TARGETS:
            write_atomic(root / rel, (HERE / 'payload' / rel).read_bytes())
        validate(root)
    except Exception:
        restore_bytes(root, originals)
        print('INSTALLATION FAILED: Original admin files restored. Backup:', backup.relative_to(root), flush=True)
        raise
    print('SUCCESS: Phase 5D.2 Destination Admin cleanup installed.')
    print('Updated ONLY: ' + ', '.join(TARGETS))
    print('To restore: python "{}" --restore "{}"'.format(Path(__file__).resolve(), backup.relative_to(root)))
    print('NEXT: Restart Django; test /admin/places/place/ and admin dashboard.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR:', error, file=sys.stderr)
        sys.exit(1)
