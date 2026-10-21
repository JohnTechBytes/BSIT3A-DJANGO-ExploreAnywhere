"""Safe Phase 6O.1 update: actionable network diagnostics and retry-errors selection.

Run from ExploreAnywhere project root, e.g.
python phase6o1_upgrade/exploreanywhere_phase6o1_network_fix.py --dry-run
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

REL = Path('apps/places/management/commands/phase6o_business_photos.py')
ORIGINAL_SHA = 'ff1919393bdf821142a2cf745e61d6c31e8bce0b734122756299df8ef687cf28'
NEW_SHA = '144182f7ba13a77c5f19c92e0200967714a35bf777c0b828a7b3603677b81a05'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def project_root():
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps' / 'places' / 'models.py').is_file():
        raise RuntimeError('Run from ExploreAnywhere project root containing manage.py.')
    return root


def validate(root):
    for args in ('check', 'help phase6o_business_photos'):
        argv = [sys.executable, 'manage.py', *args.split()]
        done = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=120)
        if done.returncode:
            raise RuntimeError('Django ' + args + ' failed:\n' + done.stdout + '\n' + done.stderr)
        print('CHECK PASSED:', args)


def restore(root, backup, current):
    path = Path(backup).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError('Backup does not exist: ' + str(path))
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        original = archive.read('original.py')
    if manifest.get('project') != str(root) or manifest.get('path') != REL.as_posix():
        raise RuntimeError('Backup belongs to a different project or path.')
    if manifest.get('previous_sha') != ORIGINAL_SHA or manifest.get('new_sha') != NEW_SHA:
        raise RuntimeError('Backup is not from Phase 6O.1.')
    if sha(original) != ORIGINAL_SHA:
        raise RuntimeError('Backup original content checksum invalid.')
    if sha(current.read_bytes()) != NEW_SHA:
        raise RuntimeError('Current photo command has been edited; refusing to overwrite it.')
    current.write_bytes(original)
    print('RESTORED:', REL)


def main():
    parser = argparse.ArgumentParser(description='Phase 6O.1 network diagnosis and targeted retry installer')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', default='')
    opts = parser.parse_args()

    root = project_root()
    current = root / REL
    if not current.is_file():
        raise RuntimeError('Phase 6O is not installed. Missing: ' + str(REL))
    if opts.restore:
        restore(root, opts.restore, current)
        return
    data = (Path(__file__).resolve().parent / 'phase6o_business_photos_v61.py').read_bytes()
    if sha(data) != NEW_SHA:
        raise RuntimeError('Installer package integrity check failed.')
    compile(data, REL.as_posix(), 'exec')
    present = sha(current.read_bytes())
    if present == NEW_SHA:
        print('ALREADY INSTALLED: Phase 6O.1 is present; no files changed.')
        return
    if present != ORIGINAL_SHA:
        raise RuntimeError('Current Phase 6O command differs from the supplied original. No changes made. Upload the current command for a compatible fix.')
    if opts.dry_run:
        print('DRY RUN OK: current Phase 6O matches; Phase 6O.1 can be installed. No files changed.')
        return

    backup_dir = root / 'phase6_backups'
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / ('phase6o1_network_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.zip')
    with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps({
            'project': str(root), 'path': REL.as_posix(),
            'previous_sha': ORIGINAL_SHA, 'new_sha': NEW_SHA,
        }, indent=2))
        archive.writestr('original.py', current.read_bytes())
    print('BACKUP:', backup)
    try:
        current.write_bytes(data)
        validate(root)
    except Exception:
        if current.exists() and sha(current.read_bytes()) == NEW_SHA:
            current.write_bytes(zipfile.ZipFile(backup).read('original.py'))
            print('ROLLBACK: previous Phase 6O command restored.')
        raise
    print('INSTALL OK: Phase 6O.1 diagnostic and failed-only retry enabled. No database changes.')
    print('TO RESTORE: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup) + '"')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
