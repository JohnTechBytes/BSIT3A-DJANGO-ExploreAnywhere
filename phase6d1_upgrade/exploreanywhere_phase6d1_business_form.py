#!/usr/bin/env python3
"""Phase 6D.1 — business-only Django Admin form polish (no migrations).

Run from the ExploreAnywhere project directory. First use --dry-run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys

TARGETS = (
    'apps/places/admin.py',
    'templates/admin/places/place/change_form.html',
)
EXPECTED_ADMIN_HASH = '7a6e6adc93a83aa6d2beaf554e80e39896d88b934ffa02d59ab519cf0f69f0cd'
BACKUP_FORMAT = 'exploreanywhere-phase6d1-business-form-v1'


def digest(data: bytes) -> str:
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def root_dir() -> Path:
    root = Path.cwd().resolve()
    if not (root / 'manage.py').is_file() or not (root / 'apps/places/models.py').is_file():
        raise RuntimeError('Run from your ExploreAnywhere project folder containing manage.py')
    return root


def collect(root: Path, pack: Path):
    state = {}
    errors = []
    for rel in TARGETS:
        target = root / rel
        source = pack / 'payload' / rel
        if not source.is_file():
            raise RuntimeError(f'Incomplete package: {source}')
        existing = target.read_bytes() if target.is_file() else None
        wanted = source.read_bytes()
        if existing is not None and b'\r\n' in existing and b'\r\n' not in wanted:
            wanted = wanted.replace(b'\n', b'\r\n')
        if existing is not None and digest(existing) == digest(wanted):
            action = 'installed'
        elif rel == 'apps/places/admin.py' and existing is not None and digest(existing) == EXPECTED_ADMIN_HASH:
            action = 'update'
        elif rel.endswith('change_form.html') and existing is None:
            action = 'create'
        else:
            action = 'block'
            errors.append('Unexpected contents in ' + rel + '; do not overwrite customized files')
        state[rel] = (action, existing, wanted)
    if errors:
        raise RuntimeError('; '.join(errors))
    return state


def backup_files(root: Path, state):
    dest = root / 'phase6_backups' / f'business-form-ui-{datetime.now():%Y%m%d-%H%M%S-%f}'
    dest.mkdir(parents=True, exist_ok=False)
    manifest = {'format':BACKUP_FORMAT, 'files':[]}
    for rel, (action, old, new) in state.items():
        if action not in ('update','create'):
            continue
        if old is not None:
            b = dest / 'originals' / rel
            b.parent.mkdir(parents=True,exist_ok=True)
            b.write_bytes(old)
        manifest['files'].append({'path': rel, 'old_existed': old is not None, 'new_hash':digest(new)})
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2), encoding='utf-8')
    return dest


def rollback(root: Path, backup: Path):
    backup = backup.resolve()
    if not backup.is_relative_to((root/'phase6_backups').resolve()):
        raise RuntimeError('Restore path must be under the project phase6_backups directory')
    mf = backup/'manifest.json'
    if not mf.is_file():
        raise RuntimeError('Backup manifest not found')
    data = json.loads(mf.read_text(encoding='utf-8'))
    if data.get('format') != BACKUP_FORMAT:
        raise RuntimeError('Incompatible backup format')
    changes = []
    for record in data['files']:
        rel = record['path']
        if rel not in TARGETS:
            raise RuntimeError('Unexpected file in manifest: ' + rel)
        original = (backup/'originals'/rel).read_bytes() if record['old_existed'] else None
        dest = root/rel
        current = dest.read_bytes() if dest.is_file() else None
        if current is not None and digest(current) != record['new_hash'] and current != original:
            raise RuntimeError('File changed since install; refusing to overwrite: ' + rel)
        if current is None and original is not None:
            raise RuntimeError('File removed since install; inspect manually: ' + rel)
        changes.append((dest, original))
    for dest,original in changes:
        if original is None:
            dest.unlink(missing_ok=True)
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(original)
    print('RESTORED original Admin files:', backup)
    print('No database records, user permissions, or migrations modified.')


def validate(root: Path):
    checks = (
        [sys.executable, 'manage.py', 'check'],
        [sys.executable, 'manage.py', 'shell', '-c',
         "from django.template.loader import get_template; "
         "from django.contrib import admin; "
         "from apps.places.models import Place; "
         "from apps.places.forms import KabankalanPlaceAdminForm; "
         "p=admin.site._registry[Place]; "
         "a=Place(slug='osm-node-123456789',city_id=2); "
         "b=Place(slug='amyan-hill',city_id=2); "
         "fs=p.get_fieldsets(None,a); "
         "fields=[f for _,spec in fs for f in spec['fields']]; "
         "legacy=[f for _,spec in p.fieldsets for f in spec['fields']]; "
         "assert len(fields)==len(set(fields)); "
         "assert set(fields)==set(legacy)|{'osm_source_link','osm_review_confirmed','osm_review_notes'}; "
         "assert p.get_fieldsets(None,b)==p.fieldsets; "
         "assert p.form is KabankalanPlaceAdminForm; "
         "get_template('admin/places/place/change_form.html'); "
         "print('PASS: Admin template, field coverage and original form protections')"],
    )
    for cmd in checks:
        print('VALIDATING:', ' '.join(cmd[1:3]),flush=True)
        p = subprocess.run(cmd,cwd=root, text=True, capture_output=True, timeout=120)
        if p.stdout.strip():print(p.stdout.rstrip())
        if p.stderr.strip(): print(p.stderr.rstrip(),file=sys.stderr)
        if p.returncode:
            raise RuntimeError(f'Validation failed with code {p.returncode}')


def main():
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--dry-run', action='store_true')
    arg.add_argument('--restore', metavar='BACKUP_FOLDER')
    args=arg.parse_args()
    root=root_dir()
    if args.restore:
        path=Path(args.restore)
        if not path.is_absolute():path=root/path
        rollback(root,path)
        return
    state=collect(root,Path(__file__).resolve().parent)
    changed=[k for k,v in state.items() if v[0] in ('create','update')]
    if not changed:
        print('ALREADY INSTALLED: Phase 6D.1 business form matches package')
        return
    print('READY: Simplify imported-business review form only.')
    print('Files:', ', '.join(changed))
    print('PRESERVED: ModelForm verification validation, native save/permissions, OSM queue, other destination editor, database and migrations.')
    if args.dry_run:
        print('DRY RUN OK: No changes made.')
        return
    backup=backup_files(root,state)
    print('BACKUP:',backup.relative_to(root),flush=True)
    try:
        for rel in changed:
            dest=root/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(state[rel][2])
        validate(root)
    except Exception as exc:
        print('INSTALL VALIDATION FAILED:',exc,'; rolling back.',file=sys.stderr)
        rollback(root,backup)
        raise RuntimeError('Installation automatically rolled back') from exc
    print('SUCCESS: Phase 6D.1 compact business verification form installed.')
    print('No changes to database, models, migrations, verification rules or published destinations.')
    print('RESTORE:',f'python "{Path(__file__).resolve()}" --restore "{backup.relative_to(root)}"')
    print('NEXT: Restart Django and open an imported OSM business from Business Review.')


if __name__=='__main__':
    try:
        main()
    except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print('ERROR:',exc,file=sys.stderr)
        sys.exit(1)
