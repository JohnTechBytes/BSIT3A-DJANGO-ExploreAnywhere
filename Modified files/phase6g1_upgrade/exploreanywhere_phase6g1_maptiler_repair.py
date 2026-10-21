#!/usr/bin/env python3
"""ExploreAnywhere Phase 6G.1 — backup-safe Nearby map tile fix.

No online fetch; no database migrations or record changes. At install time,
reads the existing *local* MapTiler key from attraction_carousel.html and copies
it into the Nearby map template without printing or bundling that key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

NEARBY_REL = Path('templates/places/nearby_places.html')
DISCOVERY_REL = Path('templates/places/attraction_carousel.html')
EXPECTED_NEARBY_SHA = '1855b4ccde0221af994a0e440626549c6c8a0faf53258c399c2aee88c79399dd'
MARKER = 'ExploreAnywhere Phase 6G.1: MapTiler nearby tile layer'
OLD_BLOCK = '''    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom:19,
      attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(resultsMap);'''
OLD_CREDIT = '''Map marker colors indicate selected or unselected locations—not hobby scores or business quality. © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>.'''
NEW_CREDIT = '''Map marker colors indicate selected or unselected locations—not hobby scores or business quality. Map tiles © <a href="https://www.maptiler.com/copyright/" target="_blank" rel="noopener noreferrer">MapTiler</a>; map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>.'''

# The template keys are scoped to the client-side JS; MapTiler public browser
# keys should be domain-restricted through MapTiler's key settings.
NEW_BLOCK_TEMPLATE = '''    // ExploreAnywhere Phase 6G.1: MapTiler nearby tile layer
    // Same MapTiler key and style URLs as the existing Discover Kabankalan map.
    const nearbyMapTilerKey = __LOCAL_KEY_LITERAL__;
    const nearbyAttribution =
      '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> ' +
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    const nearbyStreets = L.tileLayer(
      `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${nearbyMapTilerKey}`,
      {maxZoom:19, attribution:nearbyAttribution}
    );
    const nearbySatellite = L.tileLayer(
      `https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=${nearbyMapTilerKey}`,
      {maxZoom:19, attribution:nearbyAttribution}
    );
    // As on Discover Kabankalan, Hybrid is a satellite layer with a
    // translucent streets overlay (not a dedicated labels-only layer).
    const nearbyHybridSatellite = L.tileLayer(
      `https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=${nearbyMapTilerKey}`,
      {maxZoom:19, attribution:nearbyAttribution}
    );
    const nearbyHybridStreets = L.tileLayer(
      `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${nearbyMapTilerKey}`,
      {maxZoom:19, attribution:nearbyAttribution, opacity:.30}
    );
    const nearbyHybrid = L.layerGroup([nearbyHybridSatellite,nearbyHybridStreets]);
    // Tile errors are asynchronous, so the surrounding try/catch alone cannot
    // report them. Keep the result cards available when provider requests fail.
    let nearbyTileErrorShown = false;
    const nearbyTileError = () => {
      if (!nearbyTileErrorShown && mapStatus) {
        nearbyTileErrorShown = true;
        mapStatus.textContent = 'Map tiles are unavailable from MapTiler. Check your key restrictions or network connection; nearby listings and Details still work.';
      }
    };
    [nearbyStreets,nearbySatellite,nearbyHybridSatellite,nearbyHybridStreets]
      .forEach(layer => layer.on('tileerror', nearbyTileError));
    nearbyStreets.addTo(resultsMap);
    L.control.layers({
      'Detailed Streets':nearbyStreets,
      'Satellite':nearbySatellite,
      'Hybrid (Street Overlay)':nearbyHybrid
    }, null, {position:'topright', collapsed:true}).addTo(resultsMap);'''


def project_root():
    seeds = [Path.cwd(), Path(__file__).resolve().parent]
    for seed in seeds:
        for candidate in (seed, *seed.parents):
            if (candidate / 'manage.py').is_file() and (candidate / NEARBY_REL).is_file():
                return candidate
    raise RuntimeError('Run this installer inside your ExploreAnywhere Django project (manage.py not found).')


def normalized_hash(raw):
    return hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()


def read_source(root):
    nearby_path = root / NEARBY_REL
    discovery_path = root / DISCOVERY_REL
    if not discovery_path.is_file():
        raise RuntimeError(f'Missing working Discover Kabankalan map: {DISCOVERY_REL}')
    old_bytes = nearby_path.read_bytes()
    try:
        old_text = old_bytes.decode('utf-8-sig')
        discovery = discovery_path.read_text(encoding='utf-8-sig')
        # Match content independently of Windows vs Unix line endings.
        old_text = old_text.replace('\r\n','\n')
        discovery = discovery.replace('\r\n','\n')
    except UnicodeDecodeError:
        raise RuntimeError('Map templates must be UTF-8. No changes made.')
    return old_bytes, old_text, discovery


def build_patch(old_bytes, old_text, discovery):
    if MARKER in old_text:
        return None
    if normalized_hash(old_bytes) != EXPECTED_NEARBY_SHA:
        raise RuntimeError('Nearby map template has changed since the uploaded source ZIP; refusing to overwrite it. Send an updated source ZIP.')
    match = re.search(r'\bconst\s+mapTilerKey\s*=\s*([\'\"])([^\'\"\r\n]+)\1\s*;', discovery)
    if not match:
        raise RuntimeError('Could not find the existing MapTiler key in the working Discover Kabankalan template. No changes made.')
    map_key = match.group(2)
    if not map_key or not re.fullmatch(r'[A-Za-z0-9_\-]+',map_key):
        raise RuntimeError('Existing MapTiler key has an unexpected format. No changes made.')
    for required in ('https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${mapTilerKey}',
                     'https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=${mapTilerKey}'):
        if required not in discovery:
            raise RuntimeError('Working MapTiler map configuration differs from the tested version. No changes made.')
    if old_text.count(OLD_BLOCK) != 1 or old_text.count(OLD_CREDIT) != 1:
        raise RuntimeError('Nearby tile layer/attribution did not match source; no changes made.')
    new_block = NEW_BLOCK_TEMPLATE.replace('__LOCAL_KEY_LITERAL__',json.dumps(map_key))
    modified = old_text.replace(OLD_BLOCK,new_block,1).replace(OLD_CREDIT,NEW_CREDIT,1)
    if modified.count(MARKER) != 1 or 'tile.openstreetmap.org' in modified:
        raise RuntimeError('Patched Nearby map did not pass static checks; no changes made.')
    if b'\r\n' in old_bytes:
        modified = modified.replace('\n','\r\n')
    elif '\r\n' in old_text:
        raise RuntimeError('Mixed line endings, no changes made.')
    encoded = modified.encode('utf-8')
    if old_bytes.startswith(b'\xef\xbb\xbf'):
        encoded = b'\xef\xbb\xbf'+encoded
    return encoded


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp = tempfile.mkstemp(prefix='.ea6g1-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def validate_django(root):
    commands = [
        [sys.executable,'manage.py','check'],
        [sys.executable,'manage.py','shell','-c',"from django.template.loader import get_template; get_template('places/nearby_places.html'); get_template('places/attraction_carousel.html'); print('PASS: Django map templates compile')"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd,cwd=root,text=True,capture_output=True,timeout=65)
        if result.stdout: print(result.stdout.strip())
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or 'Unknown Django validation error').strip()[:2200])


def install(root,dry_run):
    target=root/NEARBY_REL
    old_bytes,old_text,discovery=read_source(root)
    new_bytes=build_patch(old_bytes,old_text,discovery)
    if new_bytes is None:
        print('ALREADY INSTALLED: Phase 6G.1 MapTiler tile repair detected. No changes made.')
        return
    if dry_run:
        print('DRY RUN OK: Nearby map tile repair is compatible with your uploaded templates.')
        print('Will change ONLY: templates/places/nearby_places.html')
        print('Uses existing local MapTiler browser key without including it in this installer or printing it.')
        print('Preserves: verified-only search, markers, Leaflet lazy loading, distances, database and MapTiler Discover map.')
        return
    identifier='nearby-tiles-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    backup=root/'phase6_backups'/identifier
    backup_file=backup/NEARBY_REL
    backup_file.parent.mkdir(parents=True,exist_ok=False)
    backup_file.write_bytes(old_bytes)
    manifest={
        'target':NEARBY_REL.as_posix(),
        'original_sha256':hashlib.sha256(old_bytes).hexdigest(),
        'patched_sha256':hashlib.sha256(new_bytes).hexdigest(),
        'version':'phase6g1',
    }
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('BACKUP:', backup.relative_to(root))
    try:
        atomic_write(target,new_bytes)
        print('VALIDATING: Django system check and updated map templates')
        validate_django(root)
        print('SUCCESS: Phase 6G.1 Nearby map now uses your existing MapTiler provider.')
        print('Updated ONLY:', NEARBY_REL)
        print('No database, migrations, access permissions, or published places changed.')
        print('RESTORE: python "{}" --restore "{}"'.format(Path(__file__).resolve(),backup.relative_to(root)))
        print('NEXT: Restart Django; test Near Me map and verify tiles load on desktop and Android.')
    except Exception as e:
        atomic_write(target,old_bytes)
        print('FAILED: Django validation failed; original Nearby template restored.',file=sys.stderr)
        print('Reason:',str(e)[:1900],file=sys.stderr)
        raise SystemExit(1)


def restore(root,backup_arg):
    backup=Path(backup_arg)
    if not backup.is_absolute():
        backup=(root/backup).resolve()
    expected_dir=(root/'phase6_backups').resolve()
    if expected_dir not in backup.parents:
        raise RuntimeError('Restore path must be inside your project phase6_backups folder.')
    info_path=backup/'manifest.json'
    if not info_path.is_file():
        raise RuntimeError('Backup manifest not found. Nothing restored.')
    info=json.loads(info_path.read_text(encoding='utf-8'))
    if info.get('target') != NEARBY_REL.as_posix() or info.get('version')!='phase6g1':
        raise RuntimeError('Incorrect backup manifest. Nothing restored.')
    target=root/NEARBY_REL
    original=(backup/NEARBY_REL).read_bytes()
    if hashlib.sha256(original).hexdigest()!=info['original_sha256']:
        raise RuntimeError('Backup was modified or corrupt. Nothing restored.')
    current=target.read_bytes()
    if hashlib.sha256(current).hexdigest() != info['patched_sha256']:
        raise RuntimeError('Current Nearby template differs from the installed patch. Refusing to overwrite newer edits.')
    atomic_write(target,original)
    print('RESTORED:',NEARBY_REL)
    print('Source file recovered exactly from:',backup)


def main():
    parser=argparse.ArgumentParser(description='Repair ExploreAnywhere Nearby map tiles using existing MapTiler configuration')
    parser.add_argument('--dry-run',action='store_true',help='Check compatibility without changing files')
    parser.add_argument('--restore',metavar='BACKUP_DIR',help='Restore from a specific Phase 6G.1 backup')
    args=parser.parse_args()
    try:
        root=project_root()
        if args.restore:
            restore(root,args.restore)
        else:
            install(root,args.dry_run)
    except (RuntimeError,FileNotFoundError,PermissionError) as exc:
        print('ERROR:',str(exc),file=sys.stderr)
        sys.exit(1)

if __name__=='__main__':
    main()
