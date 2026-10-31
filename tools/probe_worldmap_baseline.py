"""Settle the world-map baseline difference between the two careers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
FILES = ["Careerc8fa1bc8-Chapter0", "Careerb191e387-Chapter0", "Careerb191e387-Chapter1",
         "Careerc8fa1bc8-Mission"]


def main() -> int:
    for name in FILES:
        path = SAVE_DIR / name
        if not path.exists():
            print(f"missing {name}")
            continue
        save = p.load(path)
        agent = next(a for a in save.agents if a.index == 2)
        keys = save.world_map
        half = len(keys) // 2
        print(f"{name:32s} v{agent.version} keys {len(keys):3d} "
              f"list1 {half} list2 {len(keys) - half if half else 0}")
        for key in keys[:3]:
            print(f"    {key}")
        if len(keys) > 3:
            print(f"    … {keys[-1]} (last)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
