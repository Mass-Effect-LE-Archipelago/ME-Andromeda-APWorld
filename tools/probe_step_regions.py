"""Infer where the story goes at each step: which regions gain named checks between saves."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
LADDER = ["Careerb191e387-Chapter0", "Careerb191e387-Chapter1", "Careerb191e387-Chapter51",
          "Careerb191e387-Chapter30", "Careerb191e387-Chapter4", "Careerb191e387-Chapter31",
          "Careerb191e387-Chapter6", "Careerb191e387-Chapter53", "Careerb191e387-Chapter33",
          "Careerb191e387-0ManualSave", "Careerb191e387-Chapter34", "Careerb191e387-Chapter10"]


def main() -> int:
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c for c in catalogue}
    previous = None
    for name in LADDER:
        path = SAVE_DIR / name
        if not path.exists():
            continue
        save = p.load(path)
        current = {g for g, v in save.plot.get("bools", {}).items() if v is True}
        if previous is not None:
            new = current - previous
            by_region = Counter(named[g]["region"] for g in new if g in named)
            top = ", ".join(f"{r} {n}" for r, n in by_region.most_common(4))
            print(f"{save.header.get('entry1', ''):22s} +{len(new):5d} flags, "
                  f"{sum(by_region.values()):3d} named -> {top}")
        previous = current
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
