"""Find a win-condition flag among the named checks.

Looks for Meridian / finale / completion vocabulary in check names and source assets, then
verifies each candidate against both reference saves (a real win flag should be true in both,
since both playthroughs finished the game).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

PATTERN = re.compile(r"(m7|meridian|finale|final_|complete|victory|endgame|archangel|archon)", re.I)
SAVES = {
    "99.5%": Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave",
    "87.4%": Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Careered8233e3-0ManualSave",
}


def main() -> int:
    checks = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    values = {}
    for label, path in SAVES.items():
        save = p.load(path)
        table = {}
        for kind in ("bools", "ints", "floats"):
            table.update(save.plot.get(kind, {}))
        values[label] = table

    hits = [c for c in checks if PATTERN.search(c["label"]) or PATTERN.search(c.get("best_source", ""))]
    print(f"candidates: {len(hits)}")
    scored = []
    for c in hits:
        both_true = all(values[label].get(c["guid"]) is True for label in SAVES)
        any_true = any(values[label].get(c["guid"]) is True for label in SAVES)
        score = (2 if both_true else 0) + (1 if any_true else 0)
        scored.append((score, c))
    scored.sort(key=lambda s: (-s[0], s[1]["name"]))
    for score, c in scored[:30]:
        vals = ", ".join(f"{label}={values[label].get(c['guid'], 'absent')}" for label in SAVES)
        print(f"  score {score}  {c['kind']:5s} {c['name'][:70]:70s} {vals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
