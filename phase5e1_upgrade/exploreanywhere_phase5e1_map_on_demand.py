#!/usr/bin/env python3
"""ExploreAnywhere Phase 5E.1 — lazy Leaflet loading. No DB or migration writes."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REL = Path("templates/places/attraction_carousel.html")
ORIG_LF = "29942c92266c45025236a074222ff3d6c255ad135d41d21c15718593875f07e9"
ORIG_CRLF = "6c1ac0c00231666a95b8aefd66dad69584d46cceba0c9ef33237ffb91cbe409e"
NEW_LF = "daa707399768757bde0c3f2cf7ab62e7ed78659152cc608f7806215d8369380d"
NEW_CRLF = "c0a319e31ed88b4932e806d218a0cc72205cb49665cc5c2f601af3961b4537ae"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def find_project():
    work = Path.cwd().resolve()
    if (work / "manage.py").is_file():
        return work
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").is_file():
            return parent
    raise RuntimeError("Run this installer from the ExploreAnywhere folder containing manage.py.")

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".ea5e-", delete=False) as f:
            tmp = Path(f.name)
            f.write(data)
        os.replace(str(tmp), str(path))
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()

def ensure_payload():
    payload = (Path(__file__).resolve().parent / "payload" / "attraction_carousel.html")
    if not payload.is_file():
        raise RuntimeError("Payload missing. Extract the complete ZIP, including payload/.")
    data = payload.read_bytes()
    if sha(data) != NEW_LF:
        raise RuntimeError("Unexpected payload checksum. Extract a fresh copy of the ZIP.")
    return data

def validate(root):
    tests = [
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "shell", "-c",
         "from django.template.loader import get_template; "
         "get_template('places/attraction_carousel.html'); print('PASS: Places template loads')"],
    ]
    for cmd in tests:
        print("VALIDATING:", " ".join(cmd[1:]))
        run = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=120)
        if run.stdout.strip():
            print(run.stdout.rstrip())
        if run.returncode:
            if run.stderr.strip(): print(run.stderr.rstrip())
            raise RuntimeError("Django validation failed; the original template will be restored.")

def restore(root, backup_name):
    folder = (root / backup_name).resolve()
    backups = (root / "phase5_backups").resolve()
    if folder == backups or backups not in folder.parents:
        raise RuntimeError("Restore must point to a folder inside phase5_backups.")
    manifest = folder / "manifest.json"
    original = folder / REL
    if not manifest.is_file() or not original.is_file():
        raise RuntimeError("Backup manifest or original file is missing.")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    before = original.read_bytes()
    if sha(before) != metadata["original_sha256"]:
        raise RuntimeError("Backup integrity failure; refusing to restore.")
    current = (root / REL).read_bytes()
    if sha(current) not in (metadata["installed_sha256"], metadata["original_sha256"]):
        raise RuntimeError("Current template has new edits; refusing to overwrite during restoration.")
    atomic_write(root / REL, before)
    print("RESTORED:", REL)
    print("Source returned to the exact pre-upgrade content and line endings.")

def install(root, dry_run=False):
    payload = ensure_payload()
    target = root / REL
    if not target.is_file():
        raise RuntimeError("Places template missing: " + str(REL))
    before = target.read_bytes()
    digest = sha(before)
    if digest in (NEW_LF, NEW_CRLF):
        print("ALREADY INSTALLED: Phase 5E.1 template matches this package.")
        return
    if digest not in (ORIG_LF, ORIG_CRLF):
        raise RuntimeError(
            "STOP: Places template differs from the uploaded Phase 5E source. "
            "No files changed. Send the latest template for compatibility review."
        )
    updated = payload if digest == ORIG_LF else payload.replace(b"\n", b"\r\n")
    expected = NEW_LF if digest == ORIG_LF else NEW_CRLF
    if sha(updated) != expected:
        raise RuntimeError("Line ending conversion failed; no files changed.")
    if dry_run:
        print("DRY RUN OK: Phase 5E.1 on-demand Leaflet patch matches the uploaded source.")
        print("Changes ONLY:", REL)
        print("Leaflet loads on Map View; no-coordinate results avoid map downloads.")
        print("Preserves MapTiler layers/key, scores, search, views, models, data and Admin.")
        return

    backup_dir = root / "phase5_backups" / (
        "map-on-demand-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    source_copy = backup_dir / REL
    source_copy.parent.mkdir(parents=True,exist_ok=True)
    atomic_write(source_copy,before)
    (backup_dir / "manifest.json").write_text(json.dumps({
        "original_sha256": sha(before),
        "installed_sha256": sha(updated),
        "target": str(REL),
    }, indent=2),encoding="utf-8")
    print("BACKUP:", backup_dir.relative_to(root))
    try:
        atomic_write(target, updated)
        validate(root)
    except Exception as error:
        atomic_write(target, before)
        print("INSTALL VALIDATION FAILED. ORIGINAL TEMPLATE RESTORED.")
        raise RuntimeError(str(error)) from error

    print("SUCCESS: Phase 5E.1 on-demand Map View installed.")
    print("Modified ONLY:", REL)
    print("No database, migrations, map provider, recommendation or Admin changes.")
    print("Rollback: python", '"' + str(Path(__file__).resolve()) + '"',
          "--restore", '"' + str(backup_dir.relative_to(root)) + '"')
    print("NEXT: Restart Django; test List View, Map View and card-to-map on Android.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--restore",metavar="BACKUP_FOLDER")
    args=p.parse_args()
    try:
        root=find_project()
        if args.restore:
            restore(root,args.restore)
        else:
            install(root,dry_run=args.dry_run)
    except Exception as exc:
        print("ERROR:",exc)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
