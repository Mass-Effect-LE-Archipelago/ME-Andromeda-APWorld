"""Check whether each weapon research project has a unique BoolProvider plot-flag condition.

If the third flag on a research-project asset differs per weapon, it is a per-weapon flag and
could be a delivery target. If it is shared, weapons are not addressable through plot flags.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOINS = [ROOT / "tools" / "scratch" / "join-sweep2.json", ROOT / "tools" / "scratch" / "join-sweep.json"]
NAME = re.compile(r"researchproject_weapon_[a-z]+_([a-z0-9_]+?)(?:_\d+)?$", re.I)


def main() -> int:
    save = json.loads((ROOT / "docs" / "Career870ee94.plot.json").read_text(encoding="utf-8"))
    values = {}
    for kind in ("bools", "ints", "floats"):
        values.update(save.get(kind, {}))

    per_weapon: dict[str, set[str]] = {}
    for join in JOINS:
        data = json.loads(join.read_text(encoding="utf-8"))
        for asset in data.get("assets", []):
            match = NAME.search(asset["name"].lower())
            if not match:
                continue
            name = match.group(1)
            for flag in asset["flags"]:
                if "BoolProvider_PlotCondition" in flag["path"]:
                    per_weapon.setdefault(name, set()).add(flag["guid"])

    print(f"weapons with a BoolProvider flag: {len(per_weapon)}")
    for name in sorted(per_weapon)[:12]:
        guid = sorted(per_weapon[name])[0]
        print(f"  {name:18s} {guid}  {values.get(guid, 'absent')}")
    unique = {next(iter(v)) for v in per_weapon.values() if len(v) == 1}
    print(f"distinct guids across weapons: {len(unique)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
