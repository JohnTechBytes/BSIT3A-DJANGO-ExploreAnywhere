"""Install Phase 6O without altering any MySQL records or existing code files."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

COMMAND_PATH = Path('apps/places/management/commands/phase6o_business_photos.py')
REQUIRED_FIELDS = ('cover_image_url', 'photo_credit', 'photo_source_url', 'photo_license',
                   'photo_license_url', 'is_active', 'is_verified')


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def project():
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise RuntimeError('Run this from your ExploreAnywhere project root (with manage.py).')
    model = (root / 'apps/places/models.py').read_text(encoding='utf-8-sig')
    if any(field not in model for field in REQUIRED_FIELDS):
        raise RuntimeError('Required Place photo fields are missing; refusing incompatible install.')
    return root


def check(root):
    commands = [
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'help', 'phase6o_business_photos'],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise RuntimeError(f'Validation failed ({command[-1]}):\n{result.stdout}\n{result.stderr}')
        print('CHECK PASSED:', ' '.join(command[2:]))


def restore(root, filename, expected):
    path = Path(filename).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError('Backup ZIP does not exist.')
    target = root / COMMAND_PATH
    if target.is_file() and target.read_bytes() != expected:
        raise RuntimeError('Installed command has been edited. Refusing to overwrite; review manually.')
    with zipfile.ZipFile(path) as archive:
        meta = json.loads(archive.read('manifest.json'))
        if meta.get('project') != str(root) or meta.get('path') != COMMAND_PATH.as_posix():
            raise RuntimeError('Backup is not for this project/command.')
        if meta.get('existed'):
            target.parent.mkdir(parents=True, exist_ok=True)
            original = archive.read('original.py')
            if digest(original) != meta.get('sha256'):
                raise RuntimeError('Backup integrity mismatch.')
            target.write_bytes(original)
        elif target.exists():
            target.unlink()
    print('RESTORED:', COMMAND_PATH)


def main():
    args = argparse.ArgumentParser(description='Phase 6O protected photo review command installer')
    args.add_argument('--dry-run', action='store_true')
    args.add_argument('--restore', default='')
    options = args.parse_args()
    root = project()
    supplied = (Path(__file__).resolve().parent / 'phase6o_business_photos.py').read_bytes()
    compile(supplied, 'phase6o_business_photos.py', 'exec')
    target = root / COMMAND_PATH
    if options.restore:
        restore(root, options.restore, supplied)
        return
    if target.is_file():
        if target.read_bytes() == supplied:
            print('ALREADY INSTALLED: Phase 6O command is unchanged.')
            return
        raise RuntimeError('Command file already exists with different contents; refusing overwrite.')
    if options.dry_run:
        print('DRY RUN OK: fields present; new management command can be added; no files changed.')
        return
    backup_dir = root / 'phase6_backups'
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup_path = backup_dir / f'phase6o_photo_command_{timestamp}.zip'
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps({
            'project': str(root), 'path': COMMAND_PATH.as_posix(), 'existed': False,
            'sha256': ''
        }, indent=2))
    print('BACKUP:', backup_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_bytes(supplied)
        check(root)
    except Exception:
        if target.exists() and target.read_bytes() == supplied:
            target.unlink()
        print('ROLLBACK: new command removed; project source restored.')
        raise
    print('INSTALL OK: Phase 6O photo review command available. No database changes.')
    print('RESTORE WITH: python ' + repr(str(Path(__file__).resolve())) + ' --restore ' + repr(str(backup_path)))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
