"""Probe viability flags: are they live counters we could deliver into?

Compares every flag referenced by an asset whose path mentions 'viability' across the two
reference saves. A live counter changes with progress; a one-shot threshold marker does not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVES = {
    "87%": Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Careered8233e3-0ManualSave",
    "99%": Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave",
}
JOINS = ["tools/scratch/join-sweep.json", "docs/plot-flag-join.json", "tools/scratch/join-conv.json",
         "tools/scratch/join-sweep2.json"]


def main() -> int:
    plots = {label: p.load(path) for label, path in SAVES.items()}

    def value(label: str, guid: str):
        plot = plots[label].plot
        for kind in ("bools", "ints", "floats"):
            if guid in plot.get(kind, {}):
                return plot[kind][guid]
        return "absent"

    found: dict[tuple[str, str], None] = {}
    for src in JOINS:
        path = ROOT / src
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for asset in data.get("assets", []):
            if "viability" not in asset["name"].lower():
                continue
            for flag in asset.get("flags", []):
                found[(asset["name"], flag["guid"])] = None

    print(f"flags referenced by viability assets: {len(found)}")
    for name, guid in sorted(found):
        leaf = name.rsplit("/", 1)[-1]
        print(f"  {leaf[:46]:46s} {guid}  87%={value('87%', guid)!r:10s} 99%={value('99%', guid)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
