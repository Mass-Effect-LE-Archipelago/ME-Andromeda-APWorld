"""Focus on the galaxy-map gates: the arrival gate asset, system assets and destination assets.

Prints, per asset: every referenced flag with its value in the early save and in the finished
save, so the flags that a finished playthrough has set (the unlock candidates) stand out.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
EARLY = SAVE_DIR / "Careerc8fa1bc8-Chapter0"
LATE = SAVE_DIR / "Career870ee94-1ManualSave"
JOINS = ["tools/scratch/join-sweep.json", "docs/plot-flag-join.json", "tools/scratch/join-conv.json"]
WANT = re.compile(r"^game/space/(spaceobjects/components/logic|systems|destinations)/", re.I)


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    early, late = p.load(EARLY), p.load(LATE)
    ef, lf = flags(early), flags(late)
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c["name"] for c in catalogue}

    seen: set[tuple[str, str]] = set()
    rows: list[tuple[str, str, object, object, str]] = []
    for src in JOINS:
        path = ROOT / src
        if not path.exists():
            continue
        for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
            if not WANT.search(asset["name"]):
                continue
            for flag in asset.get("flags", []):
                key = (asset["name"], flag["guid"])
                if key in seen:
                    continue
                seen.add(key)
                guid = flag["guid"]
                if guid.startswith("00000000-"):
                    continue
                rows.append((asset["name"], guid, ef.get(guid, ("absent", None))[1],
                             lf.get(guid, ("absent", None))[1], named.get(guid, "")))

    print(f"space gate/system/destination flag references: {len(rows)}")
    by_asset: dict[str, list] = {}
    for row in rows:
        by_asset.setdefault(row[0], []).append(row)

    for asset in sorted(by_asset):
        entries = by_asset[asset]
        set_late = [r for r in entries if r[3] is True]
        if not set_late:
            continue
        print(f"\n{asset}   ({len(entries)} refs, {len(set_late)} true in the finished save)")
        for _, guid, early_v, late_v, label in set_late[:10]:
            print(f"   {guid}  early={early_v!r:9s} late={late_v!r:6s} {label[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
