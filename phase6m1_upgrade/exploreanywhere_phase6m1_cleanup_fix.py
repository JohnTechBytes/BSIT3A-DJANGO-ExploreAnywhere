#!/usr/bin/env python3
"""Phase 6M.1: robust, reversible cleanup of redundant Discover controls.

Supports original Phase 6F/6K and Phase 6L variants of the shared navigation.
Does not update models, DB, MapTiler, search, or Nearby JavaScript.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

FILES = (
    'templates/places/_discovery_modes.html',
    'templates/places/nearby_places.html',
)
MANIFEST = 'PHASE6M1_MANIFEST.json'


def project_root() -> Path:
    root = Path.cwd()
    if not (root / 'manage.py').is_file():
        raise RuntimeError('Open your ExploreAnywhere project folder containing manage.py first.')
    return root


def update_nav(src: str) -> tuple[str, list[str]]:
    notes = []
    nav_start = re.search(r'<nav\s+class=["\']ea6f-nav["\'][^>]*>', src)
    if not nav_start or src.count('<nav class="ea6f-nav"') != 1:
        raise RuntimeError('Shared Discover navigation is not recognized; please upload the current _discovery_modes.html.')
    end_pos = src.find('</nav>', nav_start.end())
    if end_pos < 0 or src.count('</nav>') != 1:
        raise RuntimeError('Shared Discover navigation has changed; no files modified.')
    before = src[:nav_start.start()]
    nav = src[nav_start.start():end_pos + len('</nav>')]
    after = src[end_pos + len('</nav>'):]

    for tab in ('>All Places</a>', '>Near Me</a>', '>Map View</a>'):
        if nav.count(tab) != 1:
            raise RuntimeError('Cannot safely identify all three Explore tabs: ' + tab)

    # Remove the known informational paragraph by *class*, not brittle exact wording.
    explain = re.compile(r'(?m)^[ \t]*<p\s+class=["\']ea6f-explain["\'][^>]*>[^<]*</p>[ \t]*\n?')
    nav, n = explain.subn('', nav)
    if n > 1:
        raise RuntimeError('Unexpected duplicate tab explanations; no files modified.')
    notes.append('Removed tab explanation' if n else 'Tab explanation already absent')

    # Accept either raw 6F navigation or 6L's `{% if mode != "nearby" %}` wrapper.
    cat_open = re.compile(r'<div\s+class=["\']ea6f-categories["\'][^>]*>')
    cm = list(cat_open.finditer(nav))
    if len(cm) > 1:
        raise RuntimeError('Multiple category shortcut blocks; no files modified.')
    if cm:
        opening = cm[0]
        block_end = nav.find('</div>', opening.end())
        if block_end == -1:
            raise RuntimeError('Incomplete category shortcuts; no files modified.')
        block_end += len('</div>')
        block = nav[opening.start():block_end]
        if (block.count('Popular searches:') != 1 or block.count('service=') != 5
                or block.count('<div') != 1 or block.count('</div>') != 1):
            raise RuntimeError('Category shortcut structure differs from the reviewed source; no files modified.')
        for category in ('coffee', 'restaurant', 'barber', 'mall', 'billiards'):
            if block.count('service=' + category) != 1:
                raise RuntimeError('Unexpected category shortcuts; no files modified.')
        left = opening.start()
        right = block_end
        # Include the optional Phase 6L mode wrapper only if both tags match.
        prefix = nav[:left]
        wrapper = re.search(r'(?m)^[ \t]*{%\s*if\s+active_discovery_mode\s*!=\s*["\']nearby["\']\s*%}[ \t]*\n?[ \t]*$', prefix)
        if wrapper and prefix[wrapper.end():left].strip() == '':
            tail = nav[right:]
            close = re.match(r'[ \t]*\n[ \t]*{%\s*endif\s*%}', tail)
            if not close:
                raise RuntimeError('Found an unclosed Nearby category wrapper; no files modified.')
            left = wrapper.start()
            right += close.end()
        elif re.match(r'[ \t]*\n[ \t]*{%\s*endif\s*%}',nav[right:]):
            raise RuntimeError('Found an unexpected Django endif after categories; no files modified.')
        nav = nav[:left].rstrip(' \t\n') + '\n' + nav[right:].lstrip('\n')
        notes.append('Removed duplicate Popular searches shortcuts')
    else:
        notes.append('Popular searches already absent')
    if 'ea6f-categories' in nav or 'ea6f-explain' in nav:
        raise RuntimeError('Unexpected remaining navigation controls; no files modified.')
    return before + nav + after, notes


def update_nearby(src: str) -> tuple[str, list[str]]:
    notes=[]
    if src.count('ea6-quick') < 1:
        raise RuntimeError('Nearby quick searches could not be located; no files modified.')
    back = re.compile(
        r'(?m)^[ \t]*<a\b(?=[^>]*\bclass=["\'][^"\']*\bea6-back\b[^"\']*["\'])'
        r'(?=[^>]*\?browse=all)[^>]*>'
        r'[ \t]*(?:←|&larr;|&#8592;|&#x2190;|\&\#x2190;)?[ \t]*All Places[ \t]*</a>[ \t]*\n?'
    )
    src,n=back.subn('',src)
    if n>1:
        raise RuntimeError('Multiple redundant All Places links; no files modified.')
    notes.append('Removed redundant back-to-All-Places link' if n else 'Back-to-All-Places link already absent')
    return src,notes


def transform(name: str, data: bytes) -> tuple[bytes, list[str]]:
    bom = b'\xef\xbb\xbf'
    is_bom = data.startswith(bom)
    crlf = b'\r\n' in data
    src = data.decode('utf-8-sig').replace('\r\n', '\n')
    if name == FILES[0]:
        output, notes = update_nav(src)
    elif name == FILES[1]:
        output, notes = update_nearby(src)
    else:
        raise RuntimeError('Unexpected source file')
    if crlf:
        output=output.replace('\n','\r\n')
    return (bom if is_bom else b'')+output.encode('utf-8'),notes


def create_backup(root:Path, originals:dict[str,bytes]) -> Path:
    folder=root/'phase6_backups'
    folder.mkdir(exist_ok=True)
    path=folder/('phase6m1_discovery_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.zip')
    hashes={name:sha256(content).hexdigest() for name,content in originals.items()}
    with ZipFile(path,'x',ZIP_DEFLATED) as archive:
        for name,data in originals.items(): archive.writestr(name,data)
        archive.writestr(MANIFEST,json.dumps({'files':hashes,'phase':'6M.1'},indent=2))
    return path


def restore(root:Path, backup:Path) -> None:
    with ZipFile(backup) as archive:
        manifest=json.loads(archive.read(MANIFEST))
        originals={name:archive.read(name) for name in FILES}
        for name,data in originals.items():
            if sha256(data).hexdigest()!=manifest['files'].get(name):
                raise RuntimeError('Backup checksum mismatch: '+name)
    for name in FILES:
        if not (root/name).is_file(): raise RuntimeError('Missing destination: '+name)
    for name,data in originals.items():(root/name).write_bytes(data)
    print('RESTORE OK: restored both templates from:', backup)


def validate(root:Path)->None:
    commands=[
        [sys.executable,'manage.py','check'],
        [sys.executable,'manage.py','shell','-c',
         'from django.template.loader import get_template; '
         '[get_template(n) for n in '+repr(list(FILES))+']; '
         'print("TEMPLATE CHECK OK: 2 templates compiled")'],
    ]
    for command in commands:
        result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=90)
        if result.stdout.strip(): print(result.stdout.strip())
        if result.returncode:
            raise RuntimeError('Django validation failed: '+(result.stderr or result.stdout)[-2000:])


def main()->int:
    parser=argparse.ArgumentParser(description='Phase 6M.1: compatible Discover Kabankalan duplicate-controls fix')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--restore',metavar='BACKUP_ZIP')
    args=parser.parse_args()
    try:
        root=project_root()
        if args.restore:
            restore(root,Path(args.restore).expanduser().resolve())
            return 0
        before={}; after={}
        for name in FILES:
            target=root/name
            if not target.is_file(): raise RuntimeError('Missing template: '+name)
            before[name]=target.read_bytes()
            after[name],notes=transform(name,before[name])
            for note in notes:print(' ',name,':',note)
        changed=[name for name in FILES if before[name]!=after[name]]
        if not changed:
            print('ALREADY CLEAN: no changes needed.')
            return 0
        if args.dry_run:
            print('DRY RUN OK: source is compatible; no files changed.')
            for name in changed:print('  READY:',name)
            return 0
        backup=create_backup(root,before)
        print('BACKUP:',backup)
        try:
            for name in changed:(root/name).write_bytes(after[name])
            validate(root)
        except BaseException:
            for name,data in before.items():(root/name).write_bytes(data)
            print('ROLLBACK: original templates restored; backup retained.')
            raise
        print('INSTALL OK: redundant Discover controls removed; no database changes.')
        print('TO RESTORE: python "'+str(Path(__file__).resolve())+'" --restore "'+str(backup)+'"')
        return 0
    except Exception as exc:
        print('ERROR:',str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
