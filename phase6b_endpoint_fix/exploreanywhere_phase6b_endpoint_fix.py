#!/usr/bin/env python3
"""Safely switch ExploreAnywhere Phase 6B OSM preview to an alternative Overpass host.

Only apps/places/management/commands/discover_kabankalan_businesses.py
is modified. No network requests, migrations, or DB writes occur during installation.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TARGET = Path('apps/places/management/commands/discover_kabankalan_businesses.py')
BACKUP_BASE = Path('phase6_backups')
FMT = 'phase6b-overpass-endpoint-fix-v1'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def lf(data):
    return data.replace(b'\r\n', b'\n')

def safe(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False

def write_atomic(path, data):
    tmp = path.with_name(path.name + '.phase6b-endpoint.tmp')
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', metavar='BACKUP_FOLDER')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if not (root/'manage.py').is_file():
        raise SystemExit('ERROR: Run from the ExploreAnywhere project directory containing manage.py.')
    target = root/TARGET
    if target.is_symlink() or not target.is_file() or not safe(target, root):
        raise SystemExit('ERROR: Phase 6B discovery command missing or unsafe. No changes made.')
    if args.restore:
        backup = Path(args.restore).expanduser()
        if not backup.is_absolute():
            backup = root/backup
        backup = backup.resolve()
        if not safe(backup, root/BACKUP_BASE):
            raise SystemExit('ERROR: Restore path must be inside phase6_backups.')
        manifest_file=backup/'manifest.json'
        original_file=backup/'original_discover_kabankalan_businesses.py'
        if not manifest_file.is_file() or not original_file.is_file():
            raise SystemExit('ERROR: Backup manifest or original file missing.')
        manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
        if manifest.get('format')!=FMT or manifest.get('target')!=TARGET.as_posix():
            raise SystemExit('ERROR: Backup manifest does not match this installer.')
        if sha(original_file.read_bytes())!=manifest.get('original_sha256'):
            raise SystemExit('ERROR: Backup was modified. Refusing restore.')
        if sha(target.read_bytes())!=manifest.get('installed_sha256'):
            raise SystemExit('ERROR: Command has been edited since installation. Refusing to overwrite.')
        write_atomic(target,original_file.read_bytes())
        print('RESTORED: Original Phase 6B discovery command restored. Database untouched.')
        return

    payload=Path(__file__).resolve().parent/'payload'
    orig_file=payload/'original.py'
    updated_file=payload/'updated.py'
    if not orig_file.is_file() or not updated_file.is_file():
        raise SystemExit('ERROR: Installer ZIP is not fully extracted (payload missing).')
    original=orig_file.read_bytes()
    updated=updated_file.read_bytes()
    current=target.read_bytes()
    if lf(current)==updated:
        print('ALREADY INSTALLED: Phase 6B uses the alternative endpoint and supports --overpass-endpoint.')
        return
    if lf(current)!=original:
        raise SystemExit('ERROR: Phase 6B source differs from the reviewed release. No changes made. Send the command file for review.')
    eol=b'\r\n' if b'\r\n' in current else b'\n'
    installed=updated.replace(b'\n',eol)
    compile(updated.decode('utf-8'),TARGET.as_posix(),'exec')
    if args.dry_run:
        print('DRY RUN OK: Phase 6B importer matches reviewed source.')
        print('Will change ONLY:', TARGET.as_posix())
        print('New default: https://overpass.kumi.systems/api/interpreter')
        print('Optional flag: --overpass-endpoint (kumi.systems or overpass-api.de)')
        print('No database, existing destinations, migrations, or admin changes.')
        return
    backup=root/BACKUP_BASE/('overpass-endpoint-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True,exist_ok=False)
    (backup/'original_discover_kabankalan_businesses.py').write_bytes(current)
    (backup/'manifest.json').write_text(json.dumps({
        'format':FMT,'target':TARGET.as_posix(),
        'original_sha256':sha(current),'installed_sha256':sha(installed)
    },indent=2),encoding='utf-8')
    try:
        write_atomic(target,installed)
        for cmd in (['check'], ['help','discover_kabankalan_businesses']):
            process=subprocess.run([sys.executable,'manage.py',*cmd],cwd=root,capture_output=True,text=True,timeout=90)
            if process.returncode:
                raise RuntimeError(f'Django {" ".join(cmd)} failed:\n{process.stdout}\n{process.stderr}')
            if cmd[0]=='help' and '--overpass-endpoint' not in process.stdout:
                raise RuntimeError('Django did not recognize the new --overpass-endpoint flag.')
        print('SUCCESS: Phase 6B endpoint fix installed and Django checks passed.')
        print('Default Overpass endpoint: https://overpass.kumi.systems/api/interpreter')
        print('Backup:',backup.relative_to(root))
        print('FETCH PREVIEW: python manage.py discover_kabankalan_businesses')
        print('RESTORE: python',str(Path(__file__).resolve()),'--restore',str(backup.relative_to(root)))
        print('No network request or database update was made during installation.')
    except Exception as exc:
        if sha(target.read_bytes())==sha(installed):
            write_atomic(target,current)
            print('RESTORED: Original discovery command after validation failure.')
        print('INSTALL FAILED:',exc)
        raise SystemExit(1)

if __name__=='__main__':
    main()
