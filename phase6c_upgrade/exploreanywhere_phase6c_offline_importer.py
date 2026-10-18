"""Backup-safe installer of a NEW read-only offline OSM importer management command.

Usage:
  python exploreanywhere_phase6c_offline_importer.py --dry-run
  python exploreanywhere_phase6c_offline_importer.py
  python exploreanywhere_phase6c_offline_importer.py --restore <backup-folder>
"""
from __future__ import annotations
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REL = Path('apps/places/management/commands/import_kabankalan_osm_extract.py')
SOURCE = Path(__file__).resolve().parent/'payload'/'import_kabankalan_osm_extract.py'
REQUIRED = Path('apps/places/management/commands/discover_kabankalan_businesses.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def project_root():
    here=Path.cwd().resolve()
    if (here/'manage.py').is_file() and (here/'apps/places/models.py').is_file():
        return here
    raise RuntimeError('Open your ExploreAnywhere project root (containing manage.py) before running the installer.')


def text_cmd(root, *arguments):
    return subprocess.run([sys.executable,'manage.py',*arguments],cwd=root,
                          capture_output=True,text=True,timeout=75)


def validate(root):
    result=text_cmd(root,'check')
    if result.returncode:
        raise RuntimeError('Django system check failed:\n'+result.stdout+'\n'+result.stderr)
    result=text_cmd(root,'help','import_kabankalan_osm_extract')
    if result.returncode:
        raise RuntimeError('Management command discovery failed:\n'+result.stdout+'\n'+result.stderr)
    print('PASS: Django check and offline importer command registration.')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--restore',default='')
    args=ap.parse_args()
    root=project_root()
    target=root/REL
    expected=SOURCE.read_bytes()
    if args.restore:
        folder=Path(args.restore)
        folder=folder if folder.is_absolute() else root/folder
        receipt=folder/'created.sha256'
        if not receipt.is_file():
            raise RuntimeError('Backup receipt missing; refusing to delete any source.')
        recorded=receipt.read_text(encoding='ascii').strip()
        if target.exists() and sha(target.read_bytes())!=recorded:
            raise RuntimeError('Current file was edited since installation; refusing to delete it.')
        if target.exists():
            target.unlink()
            print('RESTORED: Phase 6C command removed; existing files untouched.')
        else:
            print('ALREADY RESTORED: No Phase 6C command present.')
        return
    if not REQUIRED.is_file():
        raise RuntimeError('Phase 6B discovery command is missing; cannot safely integrate snapshot import.')
    source=REQUIRED.read_text(encoding='utf-8')
    for needle in ('def resolve_boundary_geometry','def within_boundary','def extract_candidates',
                   'def category_key', 'def validate_snapshot','def import_snapshot'):
        if needle not in source:
            raise RuntimeError(f'Existing importer lacks expected function: {needle}; refusing patch.')
    if target.exists():
        if target.read_bytes()!=expected:
            raise RuntimeError('Offline command already exists but differs from installer; refusing overwrite.')
        print('ALREADY INSTALLED: Phase 6C offline command matches this package.')
        validate(root)
        return
    if args.dry_run:
        print('DRY RUN OK: Can safely add offline OSM extract importer as a new Django command.')
        print(f'Will create ONLY: {REL.as_posix()}')
        print('No existing code, database row or migration will be changed.')
        return
    backup=root/'phase6_backups'/('offline-osm-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True,exist_ok=False)
    (backup/'created.sha256').write_text(sha(expected),encoding='ascii')
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        target.write_bytes(expected)
        validate(root)
    except Exception:
        if target.exists() and target.read_bytes()==expected:
            target.unlink()
        print('VALIDATION FAILED: created command was removed; original project unchanged.')
        raise
    print('SUCCESS: Phase 6C offline business importer installed.')
    print('RESTORE:',f'python "{Path(__file__).resolve()}" --restore "{backup}"')
    print('USAGE: python manage.py import_kabankalan_osm_extract "PATH_TO_OSM_FILE.osm.pbf"')
    print('No business records or migrations were modified.')


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        sys.exit(1)
