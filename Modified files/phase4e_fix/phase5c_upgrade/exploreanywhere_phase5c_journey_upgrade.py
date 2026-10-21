#!/usr/bin/env python3
"""ExploreAnywhere Phase 5C.1: safe, reversible template-only enhancement.

Python standard library only; no Django imports, DB access or network calls.
Run from the ExploreAnywhere project root (folder containing manage.py).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'manifest.json'
BACKUP_FOLDER = 'phase5_backups'


def normalized_bytes(data):
    return data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def path_digest(path):
    return digest(normalized_bytes(path.read_bytes()))


def is_within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def store_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmpname = tempfile.mkstemp(dir=str(path.parent), prefix='.phase5c-', suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, tmpname)
        os.replace(tmpname, path)
    finally:
        if os.path.exists(tmpname):
            os.unlink(tmpname)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Check source file compatibility without writing')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER', help='Restore a previous Phase 5C backup if no files have changed since installation')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file():
        raise RuntimeError('Open PowerShell in the ExploreAnywhere project folder containing manage.py first.')
    if args.dry_run and args.restore:
        parser.error('Use --dry-run OR --restore, not both.')
    if args.restore:
        restore(root, args.restore)
        return

    config = json.loads(MANIFEST.read_text(encoding='utf-8'))
    queued = []
    installed = []
    for rel, entry in config.items():
        dest = (root / rel).resolve()
        if not is_within(dest, root):
            raise RuntimeError('Unexpected path outside project: ' + rel)
        if not dest.is_file():
            raise RuntimeError('Missing file: ' + rel)
        current = path_digest(dest)
        patch = HERE / 'templates_patch' / entry['patch_file']
        if not patch.is_file() or path_digest(patch) != entry['target_sha256']:
            raise RuntimeError('Installer package is incomplete or modified: ' + patch.name)
        if current == entry['target_sha256']:
            installed.append(rel)
        elif current == entry['source_sha256']:
            queued.append((rel, dest, patch, entry))
        else:
            raise RuntimeError('Source differs from the reviewed file: ' + rel + '\nNo changes made. Re-upload current source for a compatible patch.')

    if args.dry_run:
        print('DRY RUN OK: Phase 5C.1 templates are compatible.')
        for rel, _, _, _ in queued: print('  READY:', rel)
        for rel in installed: print('  ALREADY INSTALLED:', rel)
        print('No database, migrations, app views, route handlers or approval rules changed.')
        return
    if not queued:
        print('ALREADY INSTALLED: Phase 5C.1 is present. No files modified.')
        return

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = (root / BACKUP_FOLDER / ('journey-ui-' + stamp)).resolve()
    backup.mkdir(parents=True, exist_ok=False)
    state = {'package': 'ExploreAnywhere Phase 5C.1', 'files': {}}
    for rel, dest, patch, entry in queued:
        copy = backup / rel
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, copy)
        state['files'][rel] = {
            'source_sha256': entry['source_sha256'],
            'target_sha256': entry['target_sha256'],
        }
    (backup / 'restore_manifest.json').write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    changed = []
    try:
        for rel, dest, patch, entry in queued:
            original = dest.read_bytes()
            newline = '\r\n' if b'\r\n' in original else '\n'
            updated = normalized_bytes(patch.read_bytes()).replace('\n', newline).encode('utf-8')
            store_bytes(dest, updated)
            if path_digest(dest) != entry['target_sha256']:
                raise RuntimeError('Installed checksum mismatch for ' + rel)
            changed.append(rel)
    except Exception:
        # Restore files that may have been modified, including a failed write.
        for rel, dest, _, _ in reversed(queued):
            copy = backup / rel
            if copy.is_file():
                store_bytes(dest, copy.read_bytes())
        raise

    print('SUCCESS: ExploreAnywhere Phase 5C.1 Journey UX improvement installed.')
    print('Updated ONLY:')
    for rel in changed: print(' -', rel)
    print('Backup:', backup.relative_to(root))
    print('Restore command: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup.relative_to(root)) + '"')
    print('Preserved: personal record ownership, trip/visit POST actions, staff approval, badges service, migrations and DB.')
    print('Next: python manage.py check ; python manage.py makemigrations --check --dry-run')


def restore(root, raw):
    backup_root = (root / BACKUP_FOLDER).resolve()
    backup = (root / raw).resolve()
    if not is_within(backup, backup_root) or backup == backup_root:
        raise RuntimeError('Restore folder must be a subdirectory under phase5_backups.')
    manifest_file = backup / 'restore_manifest.json'
    if not manifest_file.is_file():
        raise RuntimeError('No Phase 5C.1 restore manifest at ' + str(backup))
    state = json.loads(manifest_file.read_text(encoding='utf-8'))
    if state.get('package') != 'ExploreAnywhere Phase 5C.1':
        raise RuntimeError('Backup does not belong to Phase 5C.1.')
    for rel, entry in state['files'].items():
        if rel not in json.loads(MANIFEST.read_text(encoding='utf-8')):
            raise RuntimeError('Unknown backup entry: ' + rel)
        path = (root / rel).resolve()
        previous = (backup / rel).resolve()
        if not is_within(path, root) or not is_within(previous, backup) or not previous.is_file():
            raise RuntimeError('Invalid backup entry: ' + rel)
        if path_digest(previous) != entry['source_sha256']:
            raise RuntimeError('Backup checksum incorrect: ' + rel)
        if not path.is_file() or path_digest(path) != entry['target_sha256']:
            raise RuntimeError('Refusing to overwrite a file edited since this upgrade: ' + rel)
    for rel in state['files']:
        store_bytes(root / rel, (backup / rel).read_bytes())
    print('RESTORED:', ', '.join(state['files']))
    print('Backup was retained. No migrations or database data changed.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print('STOP:', exc, file=sys.stderr)
        sys.exit(1)
