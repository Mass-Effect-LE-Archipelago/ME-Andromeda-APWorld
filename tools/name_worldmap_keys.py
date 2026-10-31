"""Label the world-map keys by the story step where they first appear.

Walks the full-playthrough ladder in order and records, for every key in the WorldMap agent, the
first save it shows up in. Writes data/worldmap-keys.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
LADDER = [
    "Careerb191e387-Chapter0", "Careerb191e387-Chapter1", "Careerb191e387-Chapter51",
    "Careerb191e387-Chapter30", "Careerb191e387-Chapter4", "Careerb191e387-Chapter31",
    "Careerb191e387-Chapter6", "Careerb191e387-Chapter53", "Careerb191e387-Chapter33",
    "Careerb191e387-0ManualSave", "Careerb191e387-Chapter34", "Careerb191e387-Chapter10",
    "Careerb191e387-Mission", "Careerb191e387-5AutoSave",
]
OUT = ROOT / "data" / "worldmap-keys.json"


def main() -> int:
    first_seen: dict[str, dict] = {}
    for name in LADDER:
        path = SAVE_DIR / name
        if not path.exists():
            print(f"missing {name}")
            continue
        save = p.load(path)
        keys = save.world_map
        location = save.header.get("entry1", "")
        new = [k for k in keys if k not in first_seen]
        for key in new:
            first_seen[key] = {"step": name, "location": location,
                               "timestamp": save.data.get("timestamp_iso")}
        print(f"{name:34s} {location:18s} keys {len(keys):3d}  new {len(new):3d}")

    OUT.write_text(json.dumps({"note": "first save in which each world-map key appears",
                               "keys": first_seen}, indent=1), encoding="utf-8")
    by_step: dict[str, int] = {}
    for record in first_seen.values():
        by_step[record["step"]] = by_step.get(record["step"], 0) + 1
    print(f"\ntotal keys: {len(first_seen)}")
    for step, count in by_step.items():
        print(f"  {step:34s} {count:3d} new")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
