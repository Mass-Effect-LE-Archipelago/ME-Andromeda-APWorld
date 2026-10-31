"""Find planet-access / progression flags by diffing an EARLY save against the finished ones.

The finished saves cannot reveal progression flags (everything is already true). A save from the
first hours of a playthrough can: flags that are false there and true later are the candidates,
and the named ones tell us what they gate.

Usage:
  python probe_planet_flags.py <early-save> [--late <save>]   (defaults to the 99.5% save)
  python probe_planet_flags.py --list                          (saves found in the folder)

Output is grouped:
  1. flags that flip false -> true and are NAMED by the catalogue, sorted by region
  2. among those, planet-access candidates (names about unlocking, landing, destinations)
  3. how many planets appear already open in the early save (what the seed must be allowed to
     assume at the start)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
LATE_DEFAULT = SAVE_DIR / "Career870ee94-1ManualSave"
ACCESS_PATTERN = re.compile(
    r"(unlock|unlocked|access|landing|land(?:_|$)|destination|galaxymap|planet|arrive|arrival|"
    r"available|discovered|reveal|orbit)", re.I)
PLANETS = ["Eos", "Voeld", "Havarl", "Kadara", "Elaaden", "H-047c", "Meridian", "Nexus", "Aya"]


def saves_in_folder() -> list[Path]:
    if not SAVE_DIR.exists():
        return []
    return sorted((f for f in SAVE_DIR.iterdir() if f.is_file() and f.name.startswith("Career")),
                  key=lambda f: f.stat().st_mtime)


def flags(save) -> dict[str, tuple[str, object]]:
    out: dict[str, tuple[str, object]] = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("early", nargs="?", type=Path)
    ap.add_argument("--late", type=Path, default=LATE_DEFAULT)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    if args.list or args.early is None:
        print("saves in the folder (newest last):")
        for path in saves_in_folder():
            print(f"  {path.name}  {path.stat().st_size:>9,} bytes")
        return 0

    if not args.early.exists():
        print(f"no such save: {args.early}")
        return 1
    early = p.load(args.early)
    late = p.load(args.late)
    early_flags, late_flags = flags(early), flags(late)

    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c for c in catalogue}

    flipped = []
    for guid, (kind, value) in late_flags.items():
        if kind != "bools" or value is not True:
            continue
        if early_flags.get(guid, ("bools", False))[1] is True:
            continue
        flipped.append(guid)

    print(f"early save : {args.early.name}  ({early.data.get('save_file_name', '?')}, "
          f"{early.data.get('timestamp_iso', '?')})")
    print(f"late save  : {args.late.name}")
    print(f"flags: early {len(early_flags)}, late {len(late_flags)}")
    print(f"false -> true: {len(flipped)}")
    in_catalogue = [g for g in flipped if g in named]
    print(f"  of which named by the catalogue: {len(in_catalogue)}")

    by_region: dict[str, list[dict]] = {}
    for guid in in_catalogue:
        entry = named[guid]
        by_region.setdefault(entry["region"], []).append(entry)
    for region in sorted(by_region, key=lambda r: -len(by_region[r])):
        print(f"  {region:24s} {len(by_region[region])}")

    access = [named[g] for g in in_catalogue
              if ACCESS_PATTERN.search(named[g]["name"]) or ACCESS_PATTERN.search(named[g].get("best_source", ""))]
    print(f"\nplanet-access candidates: {len(access)}")
    for entry in access[:args.top]:
        print(f"  {entry['kind']:5s} {entry['name'][:96]}")
        print(f"        {entry['best_source'][-88:]}")

    print("\nplanets with any named flag already true in the early save:")
    for planet in PLANETS:
        hits = [g for g in early_flags
                if g in named and named[g]["region"].lower().startswith(planet.lower().split("-")[0])
                and early_flags[g][1] is True]
        if hits:
            print(f"  {planet:9s} {len(hits):4d} named flags already true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
