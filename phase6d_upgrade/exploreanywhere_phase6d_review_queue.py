#!/usr/bin/env python3
"""Phase 6D: backup-safe, no-migration Django Admin OSM candidate review queue.

Run from the ExploreAnywhere project root: python <this file> --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


FILE_MAP = {
    "apps/places/admin.py": "admin.py",
    "apps/places/forms.py": "forms.py",
    "templates/admin/base_site.html": "base_site.html",
    "templates/admin/index.html": "index.html",
    "templates/admin/places/place/change_list.html": "change_list.html",
    "templates/admin/places/place/osm_review.html": None,
}

# Grounded signatures from the user's uploaded source archive. Each is exact
# against the provided source once CRLF/LF line endings are normalized.
EXPECTED_HASHES = {
    "apps/places/admin.py": "390dfcb3a78df89e771cdbe2f52d54944bd2be96a64fdb45ac78f2b1022582b3",
    "apps/places/forms.py": "4ffe58c5d3a1face01611a7c7e9a7794ffe835eaa58adf94883df3b03b9eec45",
    "templates/admin/base_site.html": "8c3cbddb304f5960329fc60070b9d6afb1b9a39a6c8c7edf0311f4e370dd63e9",
    "templates/admin/index.html": "7e4a12f2287af4fa337236ebf36c9e01bdd472e2d492b3ff36a078750d266c40",
    "templates/admin/places/place/change_list.html": "8efc012f6a8ef4096d7d992d503349f1456a77b5ce1ea3c71a6140f54091cdb8",
}


def normalize(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def checksum(raw: bytes) -> str:
    return hashlib.sha256(normalize(raw)).hexdigest()


def project_root() -> Path:
    root = Path.cwd().resolve()
    if not (root / "manage.py").is_file() or not (root / "apps/places/models.py").is_file():
        raise RuntimeError("Open a PowerShell terminal in your ExploreAnywhere project folder (manage.py must exist).")
    return root


def payload_files(root: Path, installer_dir: Path):
    files = {}
    for rel in FILE_MAP:
        payload = installer_dir / "payload" / rel
        if not payload.is_file():
            raise RuntimeError(f"Upgrade package is incomplete: {payload}")
        target = root / rel
        original = target.read_bytes() if target.is_file() else None
        target_payload = payload.read_bytes()
        if original is not None and b"\r\n" in original and b"\r\n" not in target_payload:
            target_payload = target_payload.replace(b"\n", b"\r\n")
        files[rel] = (original, target_payload)
    return files


def determine_state(files):
    changed = []
    installed = []
    issues = []
    for rel, (original, modified) in files.items():
        if original is None:
            if rel in EXPECTED_HASHES:
                issues.append(f"Missing expected source file: {rel}")
            else:
                changed.append(rel)
        elif checksum(original) == checksum(modified):
            installed.append(rel)
        elif rel in EXPECTED_HASHES and checksum(original) == EXPECTED_HASHES[rel]:
            changed.append(rel)
        else:
            issues.append(f"Unrecognized edits in {rel}; refusing to overwrite your changes")
    return changed, installed, issues


def validate(root: Path):
    commands = [
        ([sys.executable, "manage.py", "check"], "Django system check"),
        ([sys.executable, "manage.py", "shell", "-c",
          "from django.template.loader import get_template; "
          "from django.urls import reverse; "
          "[get_template(x) for x in ['admin/index.html', "
          "'admin/places/place/change_list.html', "
          "'admin/places/place/osm_review.html']]; "
          "assert reverse('admin:places_place_osm_review').endswith('/osm-review/'); "
          "print('PASS: Admin review templates and route resolve')"],
         "Template compilation and Admin queue URL"),
    ]
    for args, label in commands:
        print(f"VALIDATING: {label}", flush=True)
        result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=90)
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"{label} failed (exit status {result.returncode})")


def write_files(root: Path, files, changed):
    for rel in changed:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(files[rel][1])


def make_backup(root: Path, files, changed):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = root / "phase6_backups" / f"business-review-{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    manifest = {"format": "exploreanywhere-phase6d-restore-v1", "files": []}
    for rel in changed:
        original, modified = files[rel]
        dest = backup / "originals" / rel
        if original is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(original)
        manifest["files"].append({
            "path": rel,
            "original_existed": original is not None,
            "new_hash": checksum(modified),
        })
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return backup


def restore(root: Path, backup: Path):
    backups_root = (root / "phase6_backups").resolve()
    backup = backup.resolve()
    if not backup.is_relative_to(backups_root):
        raise RuntimeError("Restore folder must be inside this project's phase6_backups directory")
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"No restoration manifest found at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "exploreanywhere-phase6d-restore-v1":
        raise RuntimeError("Unrecognized backup format")
    planned = []
    for item in manifest.get("files", []):
        rel = item["path"]
        if rel not in FILE_MAP:
            raise RuntimeError(f"Unsafe backup path: {rel}")
        target = root / rel
        current = target.read_bytes() if target.exists() else None
        previous = (backup / "originals" / rel).read_bytes() if item["original_existed"] else None
        if item["original_existed"] and previous is None:
            raise RuntimeError(f"Missing original backup for {rel}")
        if current is not None and current != previous and checksum(current) != item["new_hash"]:
            raise RuntimeError(f"Refusing to overwrite changes made after install: {rel}")
        if current is None and item["original_existed"]:
            raise RuntimeError(f"Expected installed file missing; review manually before restoring: {rel}")
        planned.append((target, previous))
    for target, original in planned:
        if original is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
    print(f"RESTORED: Source files returned to their original state from {backup}")
    print("Database, accounts, published destinations and migrations were never changed by this installer.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", metavar="BACKUP_FOLDER")
    args = parser.parse_args()
    root = project_root()
    if args.restore:
        backup = Path(args.restore)
        if not backup.is_absolute():
            backup = root / backup
        restore(root, backup)
        return
    files = payload_files(root, Path(__file__).resolve().parent)
    changed, installed, problems = determine_state(files)
    if problems:
        raise RuntimeError("INSTALL BLOCKED: " + "; ".join(problems))
    if not changed:
        print("ALREADY INSTALLED: Phase 6D review queue files match this version")
        return
    print("READY: Phase 6D verification queue matches your uploaded Admin source.")
    print("Will update: " + ", ".join(changed))
    print("Preserves: seven published Kabankalan destinations, Django permissions, models, visits and DB.")
    print("NEW: separate OSM queue; evidence confirmation; block OSM bulk publishing.")
    if args.dry_run:
        print("DRY RUN OK: No files or database records changed.")
        return
    backup = make_backup(root, files, changed)
    print(f"BACKUP: {backup.relative_to(root)}", flush=True)
    try:
        write_files(root, files, changed)
        validate(root)
    except Exception as exc:
        print(f"INSTALL VALIDATION FAILED: {exc}; restoring source backup.", file=sys.stderr)
        restore(root, backup)
        raise RuntimeError("Installation rolled back; no source changes retained") from exc
    print("SUCCESS: Phase 6D Business Verification Queue installed.")
    print("New URL: /admin/places/place/osm-review/")
    print("NOTE: The 175 snapshot records have NOT been imported yet. Stage them only after the queue passes tests.")
    print(f'TO RESTORE: python "{Path(__file__).resolve()}" --restore "{backup.relative_to(root)}"')


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
