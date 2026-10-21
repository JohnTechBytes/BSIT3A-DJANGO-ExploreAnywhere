#!/usr/bin/env python3
"""ExploreAnywhere Phase 6J: source-locked, reversible Business Review improvements.

Run from the Django project root (directory containing manage.py):
  python phase6j_upgrade/exploreanywhere_phase6j_business_review.py --dry-run
  python phase6j_upgrade/exploreanywhere_phase6j_business_review.py
  python phase6j_upgrade/exploreanywhere_phase6j_business_review.py --restore phase6_backups/phase6j-review-...
"""
import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

FILES = {
    "apps/places/admin.py": "1d39d9ebf2d508c41510791c85c02887e74eb8cb0344837d182c42255c71e533",
    "templates/admin/places/place/osm_review.html": "771ed4a91e26a216e371bdb72c10e6cbcea00310698eccfb4ea7a1400bdf53ed",
}


def normalized_sha(blob):
    return sha256(blob.replace(b"\r\n", b"\n")).hexdigest()


def with_same_newlines(source, new):
    if b"\r\n" in source and source.count(b"\r\n") == source.count(b"\n"):
        return new.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return new


def project_root():
    root = Path.cwd().resolve()
    if not (root / "manage.py").is_file():
        raise RuntimeError("Open VS Code PowerShell in your Django project folder (contains manage.py).")
    return root


def package_payload():
    base = Path(__file__).resolve().parent / "phase6j_files"
    payload = {}
    for path in FILES:
        target = base / path
        if not target.is_file():
            raise RuntimeError(f"ZIP is missing the update file: {path}")
        payload[path] = target.read_bytes()
    return payload


def inspect(root, payload):
    statuses = {}
    for name, baseline in FILES.items():
        target = root / name
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f"Missing or unsafe project file: {name}")
        current = target.read_bytes()
        digest = normalized_sha(current)
        if digest == baseline:
            statuses[name] = "original"
        elif digest == normalized_sha(payload[name]):
            statuses[name] = "installed"
        else:
            raise RuntimeError(
                f"Source mismatch: {name}. This file differs from the uploaded Phase 6J "
                "source. No changes made. Upload the updated file for a compatible patch."
            )
    if len(set(statuses.values())) > 1:
        raise RuntimeError("Partial installation detected. No changes made; review the files before continuing.")
    return next(iter(statuses.values()))


def atomic_write(path, data):
    temp = path.with_name(path.name + ".phase6j-" + uuid4().hex + ".tmp")
    try:
        with temp.open("wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def backup_originals(root):
    dest = root / "phase6_backups" / ("phase6j-review-" + datetime.now().strftime("%Y%m%d_%H%M%S") + "-" + uuid4().hex[:8])
    for name in FILES:
        source = root / name
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    metadata = {
        "phase": "6J", "files": {
            name: sha256((dest / name).read_bytes()).hexdigest() for name in FILES
        }
    }
    (dest / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return dest


def restore(root, backup, payload, validate_current=True):
    backup = backup.resolve()
    manifest = backup / "manifest.json"
    if not manifest.is_file():
        raise RuntimeError("Restore folder has no Phase 6J manifest.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("phase") != "6J" or set(data.get("files", {})) != set(FILES):
        raise RuntimeError("Not a valid Phase 6J backup")
    replacements = {}
    for name in FILES:
        original = backup / name
        if not original.is_file() or sha256(original.read_bytes()).hexdigest() != data["files"][name]:
            raise RuntimeError(f"Backup corrupted or missing: {name}")
        if normalized_sha(original.read_bytes()) != FILES[name]:
            raise RuntimeError(f"Unexpected original content in backup: {name}")
        target = root / name
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f"Unsafe or missing target during restore: {name}")
        if validate_current and normalized_sha(target.read_bytes()) not in (
            FILES[name], normalized_sha(payload[name])
        ):
            raise RuntimeError(f"Refusing to overwrite new edits during restore: {name}")
        replacements[name] = original.read_bytes()
    for name, blob in replacements.items():
        atomic_write(root / name, blob)


def validate_django(root):
    checks = [
        ([sys.executable, "manage.py", "check"], "Django system check"),
        ([sys.executable, "manage.py", "shell", "-c",
          "from django.template.loader import get_template; "
          "get_template('admin/places/place/osm_review.html'); "
          "print('Business Review template compiled successfully')"],
         "Django template compilation"),
    ]
    for cmd, label in checks:
        print("Checking:", label, flush=True)
        process = subprocess.run(cmd, cwd=root, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=100)
        if process.stdout:
            print(process.stdout.strip()[:5000], flush=True)
        if process.returncode:
            raise RuntimeError(f"{label} failed (exit {process.returncode})")


def main():
    ap = argparse.ArgumentParser(description="Phase 6J safe Admin Business Review upgrade")
    ap.add_argument("--dry-run", action="store_true", help="Inspect only; no database or file writes")
    ap.add_argument("--restore", metavar="BACKUP_FOLDER", help="Restore backed-up Phase 6J source files")
    options = ap.parse_args()
    if options.dry_run and options.restore:
        ap.error("Choose --dry-run or --restore, not both")
    root = project_root()
    payload = package_payload()
    if options.restore:
        restore(root, Path(options.restore), payload)
        print("RESTORED: Phase 6J source files from", options.restore)
        return
    state = inspect(root, payload)
    if state == "installed":
        print("ALREADY INSTALLED: Phase 6J files match the package; nothing was changed.")
        return
    print("Source match OK. Changes: apps/places/admin.py and Business Review template only.")
    print("No models, migrations, records, publication states, or other pages are modified.")
    if options.dry_run:
        print("DRY RUN OK: Phase 6J is compatible with the uploaded Business Review source.")
        return
    backup = backup_originals(root)
    print("BACKUP:", backup, flush=True)
    try:
        for name in FILES:
            target = root / name
            atomic_write(target, with_same_newlines(target.read_bytes(), payload[name]))
        for name in FILES:
            if normalized_sha((root / name).read_bytes()) != normalized_sha(payload[name]):
                raise RuntimeError(f"Post-write checksum did not match: {name}")
        validate_django(root)
    except BaseException:
        print("INSTALL FAILED: restoring backed-up files...", file=sys.stderr, flush=True)
        restore(root, backup, payload, validate_current=False)
        print("ROLLBACK COMPLETE: original files restored.", file=sys.stderr, flush=True)
        raise
    print("INSTALLED: Phase 6J Business Review enhancements. No database changes.")
    print("RESTORE IF NEEDED: python", Path(__file__).name, "--restore", str(backup))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
