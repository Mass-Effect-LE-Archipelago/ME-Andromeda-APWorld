"""Build the release payload the launcher installs: .apworld + mods.json + optional mod set.

Layout (what the MEA branch of Installer expects):
    <out>/mass_effect_andromeda.apworld
    <out>/mods.json                 the mod inventory (titles, authors, assets, conflicts)
    <out>/mods/*.fbmod              optional: the mods the launcher stages
    <out>/SHA256SUMS.txt
    <out>/README.md

Usage:
  python build_release.py [--out dist/release] [--with-mods] [--version 0.1.0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_apworld  # noqa: E402

MOD_SOURCE = ROOT / "Mass Effect Andromeda Mods"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "release")
    ap.add_argument("--with-mods", action="store_true", help="include the .fbmod files")
    ap.add_argument("--mods-dir", type=Path, default=MOD_SOURCE)
    ap.add_argument("--version", default="0.1.0")
    args = ap.parse_args()

    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 1. the world archive
    archive = out / "mass_effect_andromeda.apworld"
    sys.argv = ["build_apworld.py", "--out", str(archive)]
    if build_apworld.main() != 0:
        raise SystemExit("world archive build failed")

    # 2. the mod inventory
    shutil.copy2(ROOT / "data" / "mods.json", out / "mods.json")

    # 3. optional mod set
    copied = 0
    if args.with_mods:
        if not args.mods_dir.exists():
            raise SystemExit(f"mods folder not found: {args.mods_dir}")
        target = out / "mods"
        target.mkdir()
        for mod in sorted(args.mods_dir.glob("*.fbmod")):
            shutil.copy2(mod, target / mod.name)
            copied += 1

    # 4. checksums + readme
    entries = [archive, out / "mods.json"]
    if args.with_mods:
        entries += sorted((out / "mods").glob("*.fbmod"))
    lines = [f"{sha256(path)}  {path.relative_to(out).as_posix()}" for path in entries]
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = json.loads((ROOT / "world" / "mass_effect_andromeda" / "archipelago.json").read_text(encoding="utf-8"))
    (out / "README.md").write_text(
        f"# {manifest['game']} {args.version}\n\n"
        f"1. Put `mass_effect_andromeda.apworld` in Archipelago's `custom_worlds/` folder.\n"
        f"2. Start the **Mass Effect Andromeda Client** from the Archipelago launcher.\n"
        f"3. The client follows the newest save in\n"
        f"   `Documents\\BioWare\\Mass Effect Andromeda\\Save` and reports checks as you play.\n\n"
        f"Checks: 5,722 plot flags. Goal: finish Meridian (the client detects the Meridian hub).\n\n"
        f"`mods.json` is the mod inventory used by the launcher's Andromeda mod manager"
        + (" and `mods/` holds the mod set it stages." if args.with_mods else ".")
        + "\n\nVerify files with `SHA256SUMS.txt`.\n",
        encoding="utf-8")

    total = sum(path.stat().st_size for path in out.rglob("*") if path.is_file())
    print(f"\nrelease {args.version} at {out}")
    print(f"  files: {len(entries) + 2}   size: {total / 1024 / 1024:.1f} MB   mods: {copied}")
    for line in lines:
        print(f"  {line.split()[0][:16]}…  {line.split('  ', 1)[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
