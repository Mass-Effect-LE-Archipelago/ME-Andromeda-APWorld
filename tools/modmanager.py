"""Mod manager for the Andromeda Archipelago launcher.

Owns what a randomizer needs and Frosty's UI does not: a saved, ordered, conflict-aware mod
profile, plus deploy/restore that is verifiable and reversible.

  profile.json  { "mods": [ {"file": "...", "enabled": true, "order": 10, "title": "..."} ],
                  "notes": "..." }

Deploy copies the enabled `.fbmod` files, in order, into a destination folder and writes
`ap-manifest.json` there. Restore deletes exactly the files that manifest lists, so a failed
experiment cannot leave the folder half-changed.

Usage:
  python modmanager.py init     <mods-dir> <profile.json>
  python modmanager.py status   <mods-dir> <profile.json>
  python modmanager.py enable   <profile.json> <mod-file> [more...]
  python modmanager.py disable  <profile.json> <mod-file> [more...]
  python modmanager.py order    <profile.json> <mod-file> <position>
  python modmanager.py conflicts <mods-dir> <profile.json>
  python modmanager.py deploy   <mods-dir> <profile.json> <dest-dir>
  python modmanager.py restore  <dest-dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbmod  # noqa: E402

MANIFEST = "ap-manifest.json"


def load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_profile(path: Path, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=1), encoding="utf-8")


def inventory(mods_dir: Path) -> dict[str, dict]:
    return {m["file"]: m for m in (fbmod.parse(p) for p in sorted(mods_dir.glob("*.fbmod")))}


def cmd_init(mods_dir: Path, profile_path: Path) -> int:
    mods = inventory(mods_dir)
    entries = []
    for index, (name, record) in enumerate(sorted(mods.items())):
        entries.append({"file": name, "enabled": True, "order": (index + 1) * 10,
                        "title": record.get("title"), "assets": len(record["assets"])})
    profile = {"mods": entries, "notes": f"created from {mods_dir}"}
    save_profile(profile_path, profile)
    print(f"wrote {profile_path} with {len(entries)} mods")
    return 0


def cmd_status(mods_dir: Path, profile_path: Path) -> int:
    profile = load_profile(profile_path)
    mods = inventory(mods_dir)
    enabled = [m for m in profile["mods"] if m["enabled"]]
    print(f"{len(profile['mods'])} mods in profile, {len(enabled)} enabled")
    for entry in sorted(profile["mods"], key=lambda m: m["order"]):
        flag = "on " if entry["enabled"] else "off"
        present = "ok" if entry["file"] in mods else "MISSING FILE"
        title = entry.get("title") or mods.get(entry["file"], {}).get("title") or entry["file"]
        print(f"  [{flag}] {entry['order']:4d}  {title:44s} {present}")
    return 0


def cmd_toggle(profile_path: Path, files: list[str], enabled: bool) -> int:
    profile = load_profile(profile_path)
    known = {m["file"] for m in profile["mods"]}
    changed = 0
    for name in files:
        target = name if name in known else next((k for k in known if k.lower() == name.lower()), None)
        if target is None:
            print(f"  not in profile: {name}")
            continue
        for entry in profile["mods"]:
            if entry["file"] == target:
                entry["enabled"] = enabled
                changed += 1
                print(f"  {target}: {'enabled' if enabled else 'disabled'}")
    save_profile(profile_path, profile)
    print(f"{changed} change(s) saved")
    return 0 if changed else 1


def cmd_order(profile_path: Path, mod_file: str, position: int) -> int:
    profile = load_profile(profile_path)
    ordered = sorted(profile["mods"], key=lambda m: m["order"])
    target = next((m for m in ordered if m["file"].lower() == mod_file.lower()), None)
    if target is None:
        print(f"not in profile: {mod_file}")
        return 1
    ordered.remove(target)
    index = max(0, min(len(ordered), position - 1))
    ordered.insert(index, target)
    for i, entry in enumerate(ordered):
        entry["order"] = (i + 1) * 10
    profile["mods"] = ordered
    save_profile(profile_path, profile)
    print(f"moved {target['file']} to position {index + 1}")
    return 0


def cmd_conflicts(mods_dir: Path, profile_path: Path) -> int:
    profile = load_profile(profile_path)
    mods = inventory(mods_dir)
    owners: dict[str, list[str]] = {}
    for entry in profile["mods"]:
        if not entry["enabled"]:
            continue
        record = mods.get(entry["file"])
        if not record:
            continue
        for asset in record["assets"]:
            owners.setdefault(asset, []).append(entry["file"])
    clashes = {a: f for a, f in owners.items() if len(f) > 1}
    print(f"{len(clashes)} asset conflict(s) among enabled mods")
    for asset, files in sorted(clashes.items()):
        winner = max(files, key=lambda f: next(m["order"] for m in profile["mods"] if m["file"] == f))
        print(f"  {asset}")
        for f in sorted(set(files)):
            mark = "WINS" if f == winner else "    "
            print(f"      {mark} {f}")
    return 0


def cmd_deploy(mods_dir: Path, profile_path: Path, dest: Path) -> int:
    profile = load_profile(profile_path)
    dest.mkdir(parents=True, exist_ok=True)
    deployed = []
    for entry in sorted(profile["mods"], key=lambda m: m["order"]):
        if not entry["enabled"]:
            continue
        src = mods_dir / entry["file"]
        if not src.exists():
            print(f"missing file, skipped: {entry['file']}")
            continue
        target = dest / entry["file"]
        shutil.copy2(src, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        deployed.append({"file": entry["file"], "order": entry["order"], "sha256": digest})
        print(f"  {entry['order']:4d}  {entry['file']}")
    manifest = {"mods": deployed, "source": str(mods_dir), "profile": str(profile_path)}
    (dest / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"deployed {len(deployed)} mod(s) to {dest} (+{MANIFEST})")
    return 0


def cmd_verify(dest: Path) -> int:
    """Check a deployed folder against its manifest (presence + SHA-256)."""
    manifest_path = dest / MANIFEST
    if not manifest_path.exists():
        print(f"no {MANIFEST} in {dest}")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = 0
    for entry in manifest["mods"]:
        target = dest / entry["file"]
        if not target.exists():
            print(f"  MISSING {entry['file']}")
            problems += 1
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            print(f"  CHANGED {entry['file']}")
            problems += 1
    print(f"verified {len(manifest['mods'])} mod(s): {problems} problem(s)")
    return 0 if problems == 0 else 1


def cmd_restore(dest: Path) -> int:
    manifest_path = dest / MANIFEST
    if not manifest_path.exists():
        print(f"no {MANIFEST} in {dest}; nothing to restore")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    removed = 0
    for entry in manifest["mods"]:
        target = dest / entry["file"]
        if target.exists():
            target.unlink()
            removed += 1
    manifest_path.unlink()
    print(f"restored {dest}: removed {removed} file(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "status", "conflicts", "deploy"):
        p = sub.add_parser(name)
        p.add_argument("mods_dir", type=Path)
        p.add_argument("profile", type=Path)
        if name == "deploy":
            p.add_argument("dest", type=Path)
    p = sub.add_parser("enable")
    p.add_argument("profile", type=Path)
    p.add_argument("files", nargs="+")
    p = sub.add_parser("disable")
    p.add_argument("profile", type=Path)
    p.add_argument("files", nargs="+")
    p = sub.add_parser("order")
    p.add_argument("profile", type=Path)
    p.add_argument("file")
    p.add_argument("position", type=int)
    p = sub.add_parser("restore")
    p.add_argument("dest", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("dest", type=Path)
    args = ap.parse_args()

    if args.cmd == "init":
        return cmd_init(args.mods_dir, args.profile)
    if args.cmd == "status":
        return cmd_status(args.mods_dir, args.profile)
    if args.cmd == "conflicts":
        return cmd_conflicts(args.mods_dir, args.profile)
    if args.cmd == "deploy":
        return cmd_deploy(args.mods_dir, args.profile, args.dest)
    if args.cmd == "enable":
        return cmd_toggle(args.profile, args.files, True)
    if args.cmd == "disable":
        return cmd_toggle(args.profile, args.files, False)
    if args.cmd == "order":
        return cmd_order(args.profile, args.file, args.position)
    if args.cmd == "restore":
        return cmd_restore(args.dest)
    if args.cmd == "verify":
        return cmd_verify(args.dest)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
