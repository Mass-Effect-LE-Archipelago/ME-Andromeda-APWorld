"""Find the Meridian victory flag: false at M7, true in the Meridian hub and later, named if possible."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
M7 = SAVE_DIR / "Careerb191e387-Chapter34"     # entering M7 (Meridian finale) - before
MERIDIAN = SAVE_DIR / "Careerb191e387-Chapter10"  # Meridian hub - after
POST = SAVE_DIR / "Careerb191e387-5AutoSave"   # post-game, on Eos


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    before, after, post = p.load(M7), p.load(MERIDIAN), p.load(POST)
    fb, fa, fp = flags(before), flags(after), flags(post)
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c for c in catalogue}

    candidates = [g for g, (kind, v) in fa.items()
                  if kind == "bools" and v is True
                  and fb.get(g, ("bools", False))[1] is not True
                  and fp.get(g, ("bools", False))[1] is True]
    print(f"{M7.name} -> {MERIDIAN.name}: {len(candidates)} flags true after and false before, "
          f"still true post-game")
    print(f"  named: {len([g for g in candidates if g in named])}")

    for guid in sorted(candidates, key=lambda g: named.get(g, {}).get("name", "\uffff")):
        entry = named.get(guid)
        if entry:
            print(f"  {guid}  [{entry['region']}] {entry['name']}  <- {entry['best_source'][-50:]}")
    print("\n-- unnamed candidates containing 'm7'/'fin' in any indexed asset --")
    hits = 0
    for src in ("tools/scratch/join-sweep.json", "docs/plot-flag-join.json"):
        path = ROOT / src
        if not path.exists():
            continue
        for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
            low = asset["name"].lower()
            if "m7" not in low and "crit_fin" not in low:
                continue
            for flag in asset.get("flags", []):
                if flag["guid"] in candidates:
                    print(f"  {flag['guid']}  {asset['name'][-70:]}")
                    hits += 1
    print(f"  ({hits} asset references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
