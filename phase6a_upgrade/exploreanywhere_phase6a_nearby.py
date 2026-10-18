#!/usr/bin/env python3
"""ExploreAnywhere Phase 6A safe offline installer. Run from project root.

Dry run: python thisfile.py --dry-run
Install: python thisfile.py
Restore: python thisfile.py --restore <printed-backup-path>
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

# Normalized SHA256 of the versions provided by the user and verified Phase 5E.1
EXPECTED_BASE = {'apps/places/views.py': '4b7a8f16ee2c19d426e067107a4d39e4199a293428908b867e74e7fd6d2b5551', 'apps/places/urls.py': '51f970fdbc12906e0904df86b814907c2db2bc471d179fa0299a7a37b14d81da', 'templates/home.html': '4985558e9478bf5ee2ee6d6e301846388b20eb00ae6c9b39b775272c6c58a908', 'templates/places/attraction_carousel.html': 'daa707399768757bde0c3f2cf7ab62e7ed78659152cc608f7806215d8369380d'}
TARGETS = (
    "apps/places/views.py",
    "apps/places/urls.py",
    "templates/home.html",
    "templates/places/attraction_carousel.html",
    "apps/places/nearby_intent.py",
    "apps/places/nearby.py",
    "templates/places/nearby_places.html",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized(data):
    return data.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def root_dir():
    root = Path.cwd().resolve()
    if not (root / "manage.py").is_file() or not (root / "apps" / "places" / "views.py").is_file():
        raise ValueError("Run this script from ExploreAnywhere's root folder containing manage.py")
    return root


def payload_dir():
    return Path(__file__).resolve().parent / "payload"


def contents_for(path, original):
    data = (payload_dir() / path).read_bytes()
    if original and b"\r\n" in original:
        data = data.replace(b"\n", b"\r\n")
    if original and original.startswith(b"\xef\xbb\xbf"):
        data = b"\xef\xbb\xbf" + data
    return data


def inspect(root):
    installed, fresh = [], []
    for name in TARGETS:
        target = root / name
        current = target.read_bytes() if target.is_file() else None
        desired = (payload_dir() / name).read_bytes()
        if current is not None and sha(normalized(current)) == sha(normalized(desired)):
            installed.append(name)
        elif name in EXPECTED_BASE and current is not None and sha(normalized(current)) == EXPECTED_BASE[name]:
            fresh.append(name)
        elif name not in EXPECTED_BASE and current is None:
            fresh.append(name)
        else:
            raise RuntimeError(
                f"STOP: {name} differs from the uploaded version or is unexpectedly present. "
                "Nothing was changed. Send an updated source ZIP for a custom patch."
            )
    if installed and fresh:
        raise RuntimeError("STOP: This installation appears partially applied. No files changed. Restore an existing backup or request assistance.")
    return "installed" if installed else "ready"


def validate(root):
    for name in TARGETS:
        if name.endswith(".py"):
            compile((root / name).read_text(encoding="utf-8-sig"), name, "exec")

    python = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    cmds = [
        [python, "manage.py", "check"],
        [python, "manage.py", "shell", "-c", (
            "from django.urls import reverse; from django.template.loader import get_template; "
            "assert reverse('places:nearby_places') == '/places/nearby/'; "
            "assert reverse('places:smart_search') == '/places/smart-search/'; "
            "get_template('places/nearby_places.html'); "
            "get_template('places/attraction_carousel.html'); "
            "get_template('home.html'); print('PASS: Phase 6A routes and templates')"
        )],
    ]
    for command in cmds:
        p = subprocess.run(command, cwd=root, env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=70, check=False)
        if p.returncode:
            raise RuntimeError("Validation failed: " + " ".join(command[1:4]) + "\n" + p.stdout[-6500:])
        print(p.stdout.strip() or "PASS")


def restore(root, path, *, internal=False):
    backup = (root / path).resolve()
    # Backups only within phase6_backups
    if not backup.is_relative_to((root / "phase6_backups").resolve()):
        raise RuntimeError("For safety, backup must be under phase6_backups/")
    manifest = json.loads((backup / "manifest.json").read_text())
    if set(manifest) != set(TARGETS):
        raise RuntimeError("Backup manifest does not match this installer")
    if not internal:
        for name, meta in manifest.items():
            path = root / name
            if not path.exists() or sha(path.read_bytes()) != meta["installed_sha256"]:
                raise RuntimeError(f"Cannot restore: {name} was modified after installation. No files changed.")
    for name, meta in manifest.items():
        dest = root / name
        if meta["existed"]:
            saved = backup / "original" / name
            data = saved.read_bytes()
            if sha(data) != meta["original_sha256"]:
                raise RuntimeError(f"Backup corruption detected: {name}")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        elif dest.exists():
            dest.unlink()
    print("RESTORED: Phase 6A original files from", backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", metavar="BACKUP_FOLDER")
    opts=parser.parse_args()
    root=root_dir()
    if opts.restore:
        restore(root,opts.restore)
        return
    state=inspect(root)
    if state=="installed":
        print("ALREADY INSTALLED: Phase 6A matches your files.")
        validate(root)
        return
    if opts.dry_run:
        print("DRY RUN OK: Phase 6A matches the uploaded source and Phase 5E.1 map upgrade.")
        print("Will change: apps/places/views.py, urls.py, templates/home.html, templates/places/attraction_carousel.html")
        print("Will add: apps/places/nearby_intent.py, nearby.py, templates/places/nearby_places.html")
        print("No migrations or database writes. GPS stays in the visitor's browser.")
        return
    backup=root / "phase6_backups" / ("nearby-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    if backup.exists():
        raise RuntimeError("Backup folder already exists, refusing overwrite")
    backup.mkdir(parents=True)
    manifest={}
    try:
        # Stage and back up ALL originals before writing.
        stage={}
        for name in TARGETS:
            dest=root/name
            current=dest.read_bytes() if dest.is_file() else None
            updated=contents_for(name,current)
            stage[name]=updated
            record={"existed":current is not None,
                    "original_sha256":sha(current) if current is not None else None,
                    "installed_sha256":sha(updated)}
            manifest[name]=record
            if current is not None:
                saved=backup/"original"/name
                saved.parent.mkdir(parents=True,exist_ok=True)
                saved.write_bytes(current)
        (backup/"manifest.json").write_text(json.dumps(manifest,indent=2))
        for name,data in stage.items():
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        print("BACKUP:",backup.relative_to(root))
        print("VALIDATING: Django check, routes and templates")
        validate(root)
    except Exception as exc:
        if manifest and (backup/"manifest.json").exists():
            restore(root,backup,internal=True)
        raise RuntimeError(f"INSTALL VALIDATION FAILED — original files restored: {exc}") from exc
    print("SUCCESS: Phase 6A Smart Nearby Places installed.")
    print("Existing searches, verified Kabankalan restrictions, map provider, admin and DB preserved.")
    print("To restore: python",f'"{Path(__file__).resolve()}"',"--restore",f'"{backup.relative_to(root)}"')
    print("Next: restart Django; test /places/nearby/ and searches from the homepage.")


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:",exc)
        sys.exit(1)
