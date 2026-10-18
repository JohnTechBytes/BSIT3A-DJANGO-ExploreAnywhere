#!/usr/bin/env python3
"""Install a new, read-only-by-default OSM business discovery command safely."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TARGETS = [
    'apps/places/management/__init__.py',
    'apps/places/management/commands/__init__.py',
    'apps/places/management/commands/discover_kabankalan_businesses.py',
]


def digest(value):
    return hashlib.sha256(value).hexdigest()


def under(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', help='Backup folder printed by a previous installation')
    args = parser.parse_args()
    project = Path.cwd().resolve()
    if not (project / 'manage.py').is_file() or not (project / 'apps/places/models.py').is_file():
        raise SystemExit('ERROR: Run from the ExploreAnywhere project directory containing manage.py.')

    if args.restore:
        backup = Path(args.restore).expanduser()
        if not backup.is_absolute():
            backup = project / backup
        backup = backup.resolve()
        allowed = project / 'phase6_backups'
        if not under(backup, allowed):
            raise SystemExit('ERROR: Restore path must be within phase6_backups.')
        manifest = backup / 'installer_manifest.json'
        if not manifest.is_file():
            raise SystemExit('ERROR: Missing backup manifest. Nothing changed.')
        records = json.loads(manifest.read_text(encoding='utf8'))
        if records.get('format') != 'phase6b-osm-installer-v1':
            raise SystemExit('ERROR: Wrong backup type.')
        created = records['created']
        # Never delete a customized file, even during a restore.
        for rel, sha in created.items():
            if rel not in TARGETS:
                raise SystemExit('ERROR: Unexpected path in restore manifest.')
            p = (project / rel).resolve()
            if not under(p, project):
                raise SystemExit('ERROR: Unsafe restore path.')
            if p.exists() and digest(p.read_bytes()) != sha:
                raise SystemExit(f'ERROR: {rel} has changed; refusing to delete it.')
        for rel in created:
            p = project / rel
            if p.exists():
                p.unlink()
                print('RESTORED: Removed new command file', rel)
        print('RESTORED: Any existing project files remain unchanged; database untouched.')
        return

    source = Path(__file__).resolve().parent / 'payload' / 'discover_kabankalan_businesses.py'
    if not source.is_file():
        raise SystemExit('ERROR: ZIP payload missing or folder not extracted completely.')
    payloads = {TARGETS[0]: b'', TARGETS[1]: b'', TARGETS[2]: source.read_bytes()}
    changed = []
    for rel, value in payloads.items():
        p = project / rel
        if p.exists():
            if p.read_bytes() != value:
                raise SystemExit(f'ERROR: Existing custom file differs: {rel}. Refusing overwrite.')
        else:
            changed.append(rel)
    if args.dry_run:
        print('DRY RUN OK: Phase 6B adds an OSM importer only; existing source unchanged.')
        print('New files:', ', '.join(changed) if changed else 'none (already installed)')
        print('No existing places or migrations will change. Preview fetch is read-only.')
        return
    if not changed:
        print('ALREADY INSTALLED: Phase 6B importer files match this package.')
        return

    backup = project / 'phase6_backups' / ('osm-importer-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    created = {}
    try:
        for rel in changed:
            p = project / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(payloads[rel])
            created[rel] = digest(payloads[rel])
        (backup / 'installer_manifest.json').write_text(json.dumps({
            'format': 'phase6b-osm-installer-v1', 'created': created,
        }, indent=2), encoding='utf8')
        for args in (['check'], ['help', 'discover_kabankalan_businesses']):
            result = subprocess.run([sys.executable, 'manage.py', *args], cwd=project,
                                    text=True, capture_output=True, timeout=90)
            if result.returncode:
                raise RuntimeError(f'manage.py {" ".join(args)} failed:\n{result.stdout}\n{result.stderr}')
        print('SUCCESS: Phase 6B OSM business discovery command installed.')
        print('Automatic backups:', backup.relative_to(project))
        print('No existing project source, models, migrations or database rows modified.')
        print('FETCH PREVIEW: python manage.py discover_kabankalan_businesses')
        print('RESTORE: python', Path(__file__), '--restore', str(backup.relative_to(project)))
    except Exception as exc:
        for rel in created:
            p = project / rel
            if p.exists() and digest(p.read_bytes()) == created[rel]:
                p.unlink()
        print('INSTALL FAILED AND ROLLED BACK:', exc)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
