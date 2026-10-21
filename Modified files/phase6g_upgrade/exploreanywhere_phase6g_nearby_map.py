#!/usr/bin/env python3
"""ExploreAnywhere Phase 6G: reversible Nearby Results Map upgrade.

Only updates templates/places/nearby_places.html; no migrations, DB writes,
existing MapTiler settings or source API keys changed.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE_HASH = "e5a034109cf2b7f96088f89af39e7462fd0b918dadc241a3e3054ccc666aae00"
UPDATED_HASH = "1855b4ccde0221af994a0e440626549c6c8a0faf53258c399c2aee88c79399dd"
TARGET = Path("templates/places/nearby_places.html")
VERSION = "ExploreAnywhere Phase 6G Nearby Results Map"


def normalized_hash(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def checked_root():
    root = Path.cwd().resolve()
    if not (root / "manage.py").is_file():
        raise RuntimeError("Run this script from the ExploreAnywhere project folder containing manage.py")
    return root


def payload_path():
    path = Path(__file__).resolve().parent / "payload" / TARGET
    if not path.is_file():
        raise RuntimeError("Missing payload in extracted ZIP: " + str(path))
    if normalized_hash(path.read_bytes()) != UPDATED_HASH:
        raise RuntimeError("Upgrade payload checksum mismatch. Extract a fresh ZIP.")
    return path


def atomic_replace(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=".phase6g-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def run_validation(root):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    cmds = [
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "shell", "-c",
         "from django.template.loader import get_template; get_template('places/nearby_places.html'); print('PASS: Phase 6G nearby template compiled')"],
    ]
    for cmd in cmds:
        print("VALIDATING:", " ".join(cmd[1:]))
        result = subprocess.run(cmd, cwd=root, env=env, text=True)
        if result.returncode:
            raise RuntimeError("Django validation failed. Original template will be restored.")


def restore(root, given):
    saved = Path(given)
    if not saved.is_absolute():
        saved = root / saved
    saved = saved.resolve()
    root_backups = (root / "phase6_backups").resolve()
    if root_backups not in saved.parents:
        raise RuntimeError("Restoration path must be inside this project's phase6_backups folder")
    manifest = saved / "manifest.json"
    backup = saved / "nearby_places.html"
    if not manifest.is_file() or not backup.is_file():
        raise RuntimeError("Backup folder is missing manifest.json or nearby_places.html")
    info = json.loads(manifest.read_text(encoding="utf-8"))
    if info.get("phase") != "phase6g" or info.get("target") != TARGET.as_posix():
        raise RuntimeError("This isn't a Phase 6G backup")
    old = backup.read_bytes()
    if sha256_bytes(old) != info.get("original_sha256"):
        raise RuntimeError("Backup contents do not match their original checksum")
    live = root / TARGET
    if not live.is_file() or normalized_hash(live.read_bytes()) != info.get("updated_normalized_hash"):
        raise RuntimeError("Live template has since changed. Refusing to overwrite newer edits.")
    atomic_replace(live, old)
    print("RESTORED:", TARGET, "from", saved)
    print("No database records were changed.")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=VERSION)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", metavar="BACKUP_FOLDER")
    args = ap.parse_args()
    root = checked_root()
    if args.restore:
        restore(root, args.restore)
        return
    payload = payload_path()
    target = root / TARGET
    if not target.is_file():
        raise RuntimeError("Missing current Nearby Places template: " + str(TARGET))
    original = target.read_bytes()
    current_hash = normalized_hash(original)
    if current_hash == UPDATED_HASH:
        print("ALREADY INSTALLED: Phase 6G Nearby Results Map matches this package.")
        if not args.dry_run:
            run_validation(root)
        return
    if current_hash != SOURCE_HASH:
        raise RuntimeError("Your Nearby Places template differs from the Phase 6F source. No files changed. Upload the newer template so we can preserve your edits.")
    print("READY:", VERSION)
    print("TARGET:", TARGET)
    print("PRESERVED: published-only Kabankalan filters, GPS/landmark sorting, Details/Directions, existing MapTiler map, admin, DB")
    print("NEW: optional on-demand map of the exact visible Nearby search results (OpenStreetMap tiles)")
    if args.dry_run:
        print("DRY RUN OK: Compatible source; no file or database changes.")
        return
    # Keep the working template's Windows line-ending convention.
    patched = payload.read_bytes()
    if b"\r\n" in original:
        patched = patched.replace(b"\n", b"\r\n")
    if normalized_hash(patched) != UPDATED_HASH:
        raise RuntimeError("Prepared template failed checksum verification")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = root / "phase6_backups" / ("nearby-results-map-" + timestamp)
    backup.mkdir(parents=True, exist_ok=False)
    (backup / "nearby_places.html").write_bytes(original)
    manifest = {
        "phase": "phase6g",
        "target": TARGET.as_posix(),
        "original_sha256": sha256_bytes(original),
        "updated_normalized_hash": UPDATED_HASH,
    }
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("BACKUP:", backup.relative_to(root))
    try:
        atomic_replace(target, patched)
        run_validation(root)
    except Exception as exc:
        atomic_replace(target, original)
        print("INSTALL FAILED: original Nearby template automatically restored.", file=sys.stderr)
        print("CAUSE:", exc, file=sys.stderr)
        raise SystemExit(1)
    print("SUCCESS: Phase 6G Nearby Results Map installed.")
    print("No changes to models, database, existing MapTiler key, imports, GPS upload, or permissions.")
    print('RESTORE: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup.relative_to(root)) + '"')
    print("NEXT: restart Django; test /places/?mode=nearby on laptop and Android.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
