#!/usr/bin/env python3
"""ExploreAnywhere Phase 6F — unified discovery, reversible source update.

Usage (from project root):
    python phase6f_upgrade/exploreanywhere_phase6f_unified.py --dry-run
    python phase6f_upgrade/exploreanywhere_phase6f_unified.py
    python phase6f_upgrade/exploreanywhere_phase6f_unified.py --restore phase6_backups/unified-... 

No database rows, models, migrations, secrets or provider settings are changed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

ORIGINAL_NORMALIZED_SHA256 = {'apps/places/views.py': '8d1ed5797ac40fba2d8bf052eb5368d4f18c3b94f2f140364715ec6925c56b1c', 'apps/places/nearby.py': 'e57e9e434048d5b94b461d6a22ce8b0cae6dd69f321d5b80bf3d94d13b6b18d5', 'templates/places/attraction_carousel.html': 'b8f51b490a1f074b1f9db8cf6a0dbd953bc02a1158a19875eac480281c0c9dfa', 'templates/places/nearby_places.html': 'f4ab55e666ed164fdf2f75164e47cd47a1bef7d603ebb5b1bba7b1f7a53b2aa0'}

NEW_PATHS = ("templates/places/_discovery_modes.html",)
ALL_PATHS = (*ORIGINAL_NORMALIZED_SHA256.keys(), *NEW_PATHS)

def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")

def digest(data: bytes) -> str:
    return hashlib.sha256(normalized(data)).hexdigest()

def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".ea6f-" + uuid4().hex + ".tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

def project_root() -> Path:
    root = Path.cwd().resolve()
    if not ((root / "manage.py").is_file() and (root / "apps/places/views.py").is_file()):
        raise RuntimeError("Run this script from the ExploreAnywhere project folder containing manage.py.")
    return root

def updated_bytes(payload: bytes, original: bytes | None) -> bytes:
    # Preserve Windows CRLF when replacing an existing Windows-style file.
    if original is not None and original.count(b"\r\n") > 0:
        linebreaks = original.count(b"\n")
        if original.count(b"\r\n") >= linebreaks * 0.80:
            return normalized(payload).replace(b"\n", b"\r\n")
    return normalized(payload)

def known_installed(root: Path, bundle: Path) -> bool:
    return all(
        (root / name).is_file() and
        digest((root / name).read_bytes()) == digest((bundle / name).read_bytes())
        for name in ALL_PATHS
    )

def verify_files(root: Path, bundle: Path) -> None:
    if known_installed(root, bundle):
        return
    for name, expected_hash in ORIGINAL_NORMALIZED_SHA256.items():
        path = root / name
        if not path.is_file():
            raise RuntimeError(f"Missing required source file: {name}")
        if digest(path.read_bytes()) != expected_hash:
            raise RuntimeError(
                f"Source has changed since the Phase 6F ZIP was prepared: {name}. "
                "No files were modified. Upload the newer file for a compatible update."
            )
    for name in NEW_PATHS:
        path = root / name
        if path.exists():
            raise RuntimeError(f"Unexpected existing file: {name}. No files modified.")

def make_backup(root: Path, bundle: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = root / "phase6_backups" / ("unified-" + stamp + "-" + uuid4().hex[:6])
    entries = []
    for name in ALL_PATHS:
        old = root / name
        if old.is_file():
            backup_path = backup / "original" / name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_bytes(old.read_bytes())
        entries.append({
            "path": name, "existed": old.is_file(),
            "installed_sha256": digest((bundle / name).read_bytes()),
        })
    (backup / "manifest.json").write_text(
        json.dumps({"phase": "6F", "files": entries}, indent=2), encoding="utf-8"
    )
    return backup

def restore(root: Path, backup: Path, force: bool = False) -> None:
    backup = backup.resolve()
    if not backup.is_relative_to((root / "phase6_backups").resolve()):
        raise RuntimeError("For safety, restoration must use a folder under phase6_backups.")
    manifest_file = backup / "manifest.json"
    if not manifest_file.is_file():
        raise RuntimeError(f"Cannot read backup manifest: {manifest_file}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("phase") != "6F":
        raise RuntimeError("Backup is not from Phase 6F.")
    # Check every path before overwriting/removing anything.
    if not force:
        for row in manifest["files"]:
            name = row["path"]
            path = root / name
            if path.is_file() and digest(path.read_bytes()) != row["installed_sha256"]:
                raise RuntimeError(
                    f"Cannot restore safely: {name} has newer changes. "
                    "Make a separate backup or seek assistance."
                )
    for row in manifest["files"]:
        name = row["path"]
        path = root / name
        if row["existed"]:
            original = backup / "original" / name
            if not original.is_file():
                raise RuntimeError(f"Backup missing original: {name}")
            write_atomic(path, original.read_bytes())
        elif path.exists():
            if path.is_file():
                path.unlink()
            else:
                raise RuntimeError(f"Unexpected directory at {name}; manual review required.")
    print("RESTORED: Original Phase 6F source and template state from", backup)

def run_django_checks(root: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    commands = [
        [sys.executable, "manage.py", "check"],
        [sys.executable, "manage.py", "shell", "-c",
         "from django.template.loader import get_template; "
         "from django.urls import resolve; "
         "[get_template(p) for p in "
         "['places/attraction_carousel.html','places/nearby_places.html','places/_discovery_modes.html']]; "
         "assert resolve('/places/').url_name == 'attraction_carousel'; "
         "assert resolve('/places/nearby/').url_name == 'nearby_places'; "
         "print('PASS: Unified templates and legacy routes resolve')"],
    ]
    for command in commands:
        print("VALIDATING:", " ".join(command[1:3]))
        result = subprocess.run(command, cwd=root, env=env, text=True)
        if result.returncode:
            raise RuntimeError(f"Django validation failed (exit code {result.returncode}).")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", metavar="BACKUP_DIR")
    args = parser.parse_args()
    root = project_root()
    bundle = Path(__file__).resolve().parent / "payload"
    for name in ALL_PATHS:
        if not (bundle / name).is_file():
            raise RuntimeError(f"Upgrade ZIP is incomplete: {name}")
    if args.restore:
        restore(root, root / args.restore)
        return
    verify_files(root, bundle)
    if known_installed(root, bundle):
        print("DRY RUN OK: Phase 6F already installed." if args.dry_run
              else "ALREADY INSTALLED: Phase 6F unified discovery matches the package.")
        return
    print("READY: Phase 6F supports unified All Places / Near Me / Map on /places/.")
    print("UPDATES:", ", ".join(ORIGINAL_NORMALIZED_SHA256))
    print("ADDS:", ", ".join(NEW_PATHS))
    print("PRESERVES: verified-only filtering, map layers, GPS privacy, ratings, models, migrations and database.")
    if args.dry_run:
        print("DRY RUN OK: No files or database records changed.")
        return
    backup = make_backup(root, bundle)
    print("BACKUP:", backup.relative_to(root))
    try:
        for name in ALL_PATHS:
            path = root / name
            original = path.read_bytes() if path.is_file() else None
            write_atomic(path, updated_bytes((bundle / name).read_bytes(), original))
        run_django_checks(root)
    except BaseException:
        print("INSTALL VALIDATION FAILED: restoring original files.")
        restore(root, backup, force=True)
        raise
    print("SUCCESS: Phase 6F unified Discover Kabankalan installed.")
    print("Open: /places/?browse=all  |  /places/?mode=nearby  |  /places/?browse=all&display=map")
    print("Old /places/nearby/ bookmarks redirect to the new unified page.")
    print("RESTORE: python", Path(__file__).resolve(), "--restore", backup.relative_to(root))
    print("No database records or migrations were changed.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
