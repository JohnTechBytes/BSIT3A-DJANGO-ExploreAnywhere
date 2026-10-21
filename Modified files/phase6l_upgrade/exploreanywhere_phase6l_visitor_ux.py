#!/usr/bin/env python3
"""ExploreAnywhere Phase 6L: reversible visitor template adjustments only."""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from patch_logic import PATCHERS, patch_content, MARKER

FILES = tuple(PATCHERS)


def find_project_root() -> Path:
    for folder in (Path.cwd(), Path(__file__).resolve().parent.parent):
        if (folder / 'manage.py').is_file():
            return folder
    raise RuntimeError('Run this command from the ExploreAnywhere project folder containing manage.py.')


def encode_update(filename: str, original: bytes) -> bytes:
    raw = original.decode('utf-8-sig')
    newline = '\r\n' if b'\r\n' in original else '\n'
    updated = patch_content(filename, raw.replace('\r\n','\n'))
    if newline == '\r\n':
        updated = updated.replace('\n', '\r\n')
    result = updated.encode('utf-8')
    if original.startswith(b'\xef\xbb\xbf'):
        result = b'\xef\xbb\xbf' + result
    return result


def write_backup(root: Path, originals: dict[str, bytes]) -> Path:
    backups = root / 'phase6_backups'
    backups.mkdir(exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    path = backups / ('phase6l_visitor_ux_' + stamp + '.zip')
    with ZipFile(path,'x',ZIP_DEFLATED) as archive:
        for name,data in originals.items():
            archive.writestr(name, data)
        archive.writestr('PHASE6L_MANIFEST.json',json.dumps({
            'upgrade':'ExploreAnywhere Phase 6L Visitor UX',
            'files':{name:sha256(data).hexdigest() for name,data in originals.items()},
        },indent=2))
    return path


def restore(root:Path, backup:Path)->None:
    if not backup.is_file():
        raise RuntimeError('Backup file was not found: '+str(backup))
    with ZipFile(backup) as archive:
        members=set(archive.namelist())
        if not set(FILES).issubset(members) or 'PHASE6L_MANIFEST.json' not in members:
            raise RuntimeError('This is not a complete Phase 6L backup.')
        manifest=json.loads(archive.read('PHASE6L_MANIFEST.json'))
        # Verify all bytes before changing any file.
        originals={name:archive.read(name) for name in FILES}
        for name,data in originals.items():
            if manifest['files'].get(name)!=sha256(data).hexdigest():
                raise RuntimeError('Backup checksum mismatch: '+name)
    for name,data in originals.items():
        destination=root/name
        if not destination.is_file():
            raise RuntimeError('Target no longer exists; restore manually: '+name)
    for name,data in originals.items():
        (root/name).write_bytes(data)
    print('RESTORED: original Phase 6L templates from',backup)


def validate_django(root:Path)->None:
    commands=[
        [sys.executable,'manage.py','check'],
        [sys.executable,'manage.py','shell','-c',
         'from django.template.loader import get_template; '
         'names='+repr(list(FILES))+'; '
         '[get_template(name) for name in names]; '
         'print("TEMPLATE CHECK OK:", len(names), "templates compiled")'],
    ]
    for cmd in commands:
        result=subprocess.run(cmd,cwd=root,text=True,capture_output=True,timeout=90)
        if result.stdout.strip(): print(result.stdout.strip())
        if result.returncode:
            raise RuntimeError('Django validation failed: '+result.stderr.strip()[:1700])


def main()->int:
    parser=argparse.ArgumentParser(description='Safe ExploreAnywhere Phase 6L visitor UI upgrade')
    parser.add_argument('--dry-run',action='store_true',help='check source compatibility; change nothing')
    parser.add_argument('--restore',metavar='BACKUP_ZIP',help='restore a Phase 6L backup')
    args=parser.parse_args()
    try:
        root=find_project_root()
        if args.restore:
            backup=Path(args.restore).expanduser().resolve()
            restore(root,backup)
            return 0
        originals={}
        changes={}
        for name in FILES:
            path=root/name
            if not path.is_file():
                raise RuntimeError('Required project file missing: '+name)
            original=path.read_bytes()
            originals[name]=original
            changes[name]=encode_update(name,original)
        if args.dry_run:
            print('DRY RUN OK: Phase 6L is compatible with all 4 current templates. No files or database records changed.')
            for name in FILES: print('  READY:',name)
            return 0
        backup=write_backup(root,originals)
        print('BACKUP:',backup)
        try:
            for name,data in changes.items():
                (root/name).write_bytes(data)
            validate_django(root)
        except Exception:
            for name,data in originals.items():
                (root/name).write_bytes(data)
            print('ROLLBACK: original files automatically restored; backup retained.')
            raise
        print('INSTALL OK: Phase 6L visitor experience updated. No models, MySQL records or MapTiler configuration changed.')
        print('TO RESTORE: python "'+str(Path(__file__).resolve())+'" --restore "'+str(backup)+'"')
        return 0
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
