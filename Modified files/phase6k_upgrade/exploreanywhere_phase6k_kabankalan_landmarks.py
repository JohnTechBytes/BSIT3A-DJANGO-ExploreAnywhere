#!/usr/bin/env python3
"""Phase 6K — optional curated Kabankalan landmark fallback for Nearby.

Safe for Phase 6H + Phase 6I. Does not change DB, map configuration, or GPS.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime

VIEW = Path('apps/places/nearby.py')
TEMPLATE = Path('templates/places/nearby_places.html')
BACKUP_PARENT = Path('phase6_backups')
MARKER_VIEW = '# ExploreAnywhere Phase 6K: curated Kabankalan reference landmarks'
MARKER_TEMPLATE = 'ExploreAnywhere Phase 6K: optional landmark reference'
# Input is the exact Phase 6H + 6I template provided and updated in prior phases.
EXPECTED_TEMPLATE = 'c0e2d4ff0a9741156a20da3507781d69d47dcd131e2e9b6e016629033f1bdc63'
EXPECTED_VIEW = 'e3d5ce3797ee71374648b2c8c8f9eadf7f75d320e1644b96ebfc0105b5406eb9'

def canonical(text):
    return text.replace('\r\n', '\n').replace('\r','\n')

def sha(text):
    return hashlib.sha256(canonical(text).encode('utf-8')).hexdigest()

def read(path):
    raw = path.read_bytes()
    return raw.decode('utf-8-sig'), '\r\n' if b'\r\n' in raw else '\n', raw.startswith(b'\xef\xbb\xbf')

def encode(text, newline, bom):
    raw = canonical(text).replace('\n', newline).encode('utf-8')
    return b'\xef\xbb\xbf'+raw if bom else raw

def replace_exact(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected exactly one source anchor, found {count}. No files changed.')
    return text.replace(old, new, 1)

def change_view(src):
    old = '''    # Only real verified point records can be reference locations.
    landmarks = list(Place.objects.filter(
        city=city, is_verified=True, is_active=True,
        latitude__isnull=False, longitude__isnull=False,
    ).order_by("title", "pk")[:100])
'''
    new = '''    # ExploreAnywhere Phase 6K: curated Kabankalan reference landmarks
    # The fallback must not become a dropdown of every future business.
    # These are previously published Kabankalan destinations; only records
    # that remain independently verified, active, and mapped are selectable.
    # Kabankalan Plaza will appear automatically once its coordinates are verified.
    kabankalan_landmark_names = (
        "Kabankalan Plaza", "CPSU Museum", "Mag Aso Falls", "Amyan Hill",
        "Maronggues Hill", "Mount Luyang", "Mount Nai-guin",
    )
    landmarks = list(Place.objects.filter(
        city=city, is_verified=True, is_active=True,
        title__in=kabankalan_landmark_names,
        latitude__isnull=False, longitude__isnull=False,
    ))
    priority = {name.casefold(): idx for idx, name in enumerate(kabankalan_landmark_names)}
    landmarks.sort(key=lambda place: priority.get(place.title.casefold(), 100))
'''
    return replace_exact(src,old,new,'curated landmark queryset')

def change_template(src):
    css = '''
/* ExploreAnywhere Phase 6K: optional landmark reference; GPS remains primary. */
.ea6k-location-top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px}
.ea6k-location-top h2{font-size:18px;color:#17345c;margin:0 0 5px}
.ea6k-location-top p{margin:0;font-size:13px;line-height:1.55;color:#506986}
.ea6k-location-top #ea6-use-gps{flex:0 0 auto}
.ea6k-landmark{margin-top:16px;border:1px solid #d6e4f2;border-radius:12px;background:#f9fbff;padding:0 14px}
.ea6k-landmark summary{font-size:13px;font-weight:800;color:#1c579e;cursor:pointer;padding:14px 0;line-height:1.5}
.ea6k-landmark summary:focus-visible{outline:3px solid #8ab8ff;outline-offset:3px}
.ea6k-landmark p{font-size:12px;color:#4b6482;line-height:1.55;margin:0 0 13px}
.ea6k-landmark-form{display:flex;align-items:end;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.ea6k-landmark-form .ea6-field{min-width:min(225px,100%);flex:1}
.ea6k-landmark-form .ea6-btn{flex:0 0 auto}
@media(max-width:760px){.ea6k-location-top{align-items:stretch}.ea6k-location-top #ea6-use-gps{flex:1 1 100%}.ea6k-landmark-form .ea6-field,.ea6k-landmark-form .ea6-btn{flex:1 1 100%}}
'''
    src = replace_exact(src, '</style>', css + '</style>', 'optional selector styles')
    old = '''    <div class="ea6-location-bar">
      <button id="ea6-use-gps" class="ea6-btn" type="button">Use my location</button>
      <form method="get" action="{% url 'places:attraction_carousel' %}" id="ea6-landmark-form" class="ea6-field">
        <input type="hidden" name="mode" value="nearby">
        <input type="hidden" name="q" value="{{ query }}">
        <input type="hidden" name="service" value="{{ selected_service }}">
        <label for="ea6-origin">Or choose a verified Kabankalan landmark</label>
        <select id="ea6-origin" name="origin">
          <option value="">Choose a landmark</option>
          {% for landmark in landmarks %}<option value="{{ landmark.pk }}" {% if selected_origin.pk == landmark.pk %}selected{% endif %}>{{ landmark.title }}</option>{% endfor %}
        </select>
      </form>
      <button type="submit" form="ea6-landmark-form" class="ea6-btn ea6-plain">Sort near landmark</button>
    </div>'''
    new = '''    <!-- ExploreAnywhere Phase 6K: optional landmark reference, Kabankalan only -->
    <div class="ea6k-location-top">
      <div>
        <h2>Find places near you</h2>
        <p>Use GPS to sort by your location and enable the distance filter.</p>
      </div>
      <button id="ea6-use-gps" class="ea6-btn" type="button">📍 Use my location</button>
    </div>
    <details class="ea6k-landmark" {% if selected_origin %}open{% endif %}>
      <summary>Can't use GPS? Choose a Kabankalan landmark instead</summary>
      <p>Optional: choose a familiar published Kabankalan landmark as a <strong>distance reference</strong>, not your current location. Only curated landmarks with staff-verified map coordinates are listed.</p>
      {% if landmarks %}
      <form method="get" action="{% url 'places:attraction_carousel' %}" id="ea6-landmark-form" class="ea6k-landmark-form">
        <input type="hidden" name="mode" value="nearby">
        <input type="hidden" name="q" value="{{ query }}">
        <input type="hidden" name="service" value="{{ selected_service }}">
        <div class="ea6-field">
          <label for="ea6-origin">Kabankalan landmark</label>
          <select id="ea6-origin" name="origin" required>
            <option value="">Select a known Kabankalan landmark</option>
            {% for landmark in landmarks %}<option value="{{ landmark.pk }}" {% if selected_origin.pk == landmark.pk %}selected{% endif %}>{{ landmark.title }}</option>{% endfor %}
          </select>
        </div>
        <button type="submit" class="ea6-btn ea6-plain">Sort from landmark</button>
      </form>
      {% else %}
      <p>There are currently no mapped, verified reference landmarks available. You can still browse verified Kabankalan places and use GPS when supported.</p>
      {% endif %}
    </details>'''
    src = replace_exact(src,old,new,'location panel')
    src = replace_exact(src,
      'Choose “Use my location” or a landmark to see nearby distances. Without a reference, results are alphabetical.',
      'Use GPS for distance sorting, or expand the optional Kabankalan landmark selector if GPS is unavailable. Without a reference, results are alphabetical.',
      'initial location instructions')
    src = replace_exact(src,
      'Phone GPS generally requires HTTPS. Use the verified landmark selector above, or test on localhost.',
      'Phone GPS generally requires HTTPS. Open the optional Kabankalan landmark selector instead, or test on localhost.',
      'GPS secure-context instructions')
    src = replace_exact(src,
      'Choose a verified landmark or allow GPS to enable distance filtering.',
      'Allow GPS or choose an optional Kabankalan landmark to enable distance filtering.',
      'distance filter instructions')
    return src

def transformed(root):
    out = {}
    for rel, func, expectation, marker in (
        (VIEW, change_view, EXPECTED_VIEW, MARKER_VIEW),
        (TEMPLATE, change_template, EXPECTED_TEMPLATE, MARKER_TEMPLATE),
    ):
        p = root/rel
        if not p.is_file(): raise ValueError('Missing required file: ' + str(rel))
        text, nl, bom = read(p)
        if marker in text:
            out[rel] = (None, None)
            continue
        if sha(text) != expectation:
            raise ValueError('Source has changed since your shared Phase 6H/6I files: '+str(rel)+'. No files changed; upload the latest file for a revised fix.')
        updated = func(canonical(text))
        if updated == canonical(text): raise ValueError('Patch had no effect: '+str(rel))
        if str(rel).endswith('.py'):
            ast.parse(updated)
        else:
            for needle in ('id="ea6-use-gps"','id="ea6h-distance"', 'id="ea6g-map"', 'nearbyMapTilerKey', 'id="ea6-origin"'):
                if needle not in updated: raise ValueError('Nearby feature unexpectedly missing: '+needle)
        out[rel] = (p.read_bytes(), encode(updated,nl,bom))
    if all(new is None for _,new in out.values()):
        return None
    if any(new is None for _,new in out.values()):
        raise ValueError('Only part of Phase 6K appears installed. Refusing to change files; please send latest source.')
    return out

def atomic_write(path, data):
    fd,temp = tempfile.mkstemp(prefix='.ea6k-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as out: out.write(data)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def validate(root):
    for args in (
        ['check'],
        ['makemigrations','--check','--dry-run'],
        ['shell','-c',"from django.template.loader import get_template; get_template('places/nearby_places.html'); print('PASS: Nearby template loads')"],
    ):
        print('VALIDATING: python manage.py '+' '.join(args[:3]),flush=True)
        proc = subprocess.run([sys.executable,'manage.py',*args],cwd=root,capture_output=True,text=True,timeout=120)
        if proc.stdout: print(proc.stdout.strip()[-1500:])
        if proc.returncode:
            if proc.stderr: print(proc.stderr[-2000:],file=sys.stderr)
            raise RuntimeError('Django validation failed. Original files will be restored.')

def restore(root, relative_backup):
    folder = (root/relative_backup).resolve()
    if root not in folder.parents or not folder.is_dir():
        raise ValueError('Backup path must be an existing subfolder of this project')
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('phase')!='6K': raise ValueError('Not a Phase 6K backup')
    entries = []
    for rel in (VIEW,TEMPLATE):
        info = manifest['files'][str(rel)]
        target = root/rel
        source = folder/rel
        old=source.read_bytes()
        if hashlib.sha256(old).hexdigest()!=info['old_sha256']:
            raise ValueError('Backup has been modified: '+str(rel))
        if hashlib.sha256(target.read_bytes()).hexdigest()!=info['new_sha256']:
            raise ValueError('Current file was edited after installation. Refusing overwrite: '+str(rel))
        entries.append((target,old))
    for target,old in entries: atomic_write(target,old)
    print('RESTORED: Both original files from',folder.relative_to(root))

def main():
    parser=argparse.ArgumentParser(description='Phase 6K — optional curated Kabankalan landmark fallback')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--restore',metavar='BACKUP_FOLDER')
    args=parser.parse_args()
    root=Path.cwd().resolve()
    if not (root/'manage.py').is_file(): raise ValueError('Run from ExploreAnywhere project root (manage.py)')
    if args.restore:
        restore(root,args.restore)
        return
    edits=transformed(root)
    if edits is None:
        print('ALREADY INSTALLED: Phase 6K curated optional landmarks.')
        return
    print('PASS: Two-file compatibility and Python syntax checks.')
    if args.dry_run:
        print('DRY RUN OK: Will change only apps/places/nearby.py and templates/places/nearby_places.html.')
        print('Kabankalan-only; manually curated verified references; no new tables, DB edits, MapTiler changes, or GPS transmission.')
        return
    folder = root/BACKUP_PARENT/('phase6k-landmarks-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,exist_ok=False)
    manifest={'phase':'6K','files':{}}
    for rel,(original,updated) in edits.items():
        dest=folder/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(original)
        manifest['files'][str(rel)]={'old_sha256':hashlib.sha256(original).hexdigest(),'new_sha256':hashlib.sha256(updated).hexdigest()}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('BACKUP:',folder.relative_to(root),flush=True)
    try:
        for rel,(original,updated) in edits.items():
            atomic_write(root/rel,updated)
        validate(root)
    except BaseException:
        for rel,(original,updated) in edits.items():
            atomic_write(root/rel,original)
        print('ROLLBACK: Original source restored. No database records were changed.',file=sys.stderr)
        raise
    print('SUCCESS: Phase 6K Kabankalan-only optional landmark selector installed.')
    print('To restore: python',Path(__file__).name,'--restore',str(folder.relative_to(root)))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        sys.exit(1)
