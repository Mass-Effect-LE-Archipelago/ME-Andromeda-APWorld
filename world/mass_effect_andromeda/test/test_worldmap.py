"""World-map key tracking over the full ladder: expect 2 keys at Kadara, 4 at M4, 4 at M5, 8 at
Meridian and nothing in between."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "world" / "mass_effect_andromeda"))

import client_core as cc  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
LADDER = ["Careerc8fa1bc8-Chapter0", "Careerc8fa1bc8-2AutoSave", "Careerc8fa1bc8-Mission",
          "Careerb191e387-Chapter0", "Careerb191e387-Chapter1", "Careerb191e387-Chapter51",
          "Careerb191e387-Chapter30", "Careerb191e387-Chapter4", "Careerb191e387-Chapter31",
          "Careerb191e387-Chapter6", "Careerb191e387-Chapter53", "Careerb191e387-Chapter33",
          "Careerb191e387-0ManualSave", "Careerb191e387-Chapter34", "Careerb191e387-Chapter10"]


def main() -> int:
    labels = json.loads((ROOT / "data" / "worldmap-keys.json").read_text(encoding="utf-8"))["keys"]
    tracker = cc.WorldMapTracker(labels)
    total = 0
    for name in LADDER:
        path = SAVE_DIR / name
        if not path.exists():
            print(f"missing {name}")
            continue
        state = cc.CareerState.read(path)
        new = tracker.poll(state)
        total += len(new)
        print(f"{name:32s} keys {len(state.world_map):3d}  new {len(new):3d}")
        for key in new[:3]:
            print(f"    {tracker.label(key)}")
    print(f"\ntotal new keys reported: {total}")
    assert tracker.poll(cc.CareerState.read(SAVE_DIR / LADDER[-1])) == [], "re-poll must be empty"
    print("PASSED: keys tracked once, re-poll is empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
