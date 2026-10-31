"""Build data/items.json (the randomizer's item pool) from the asset name index.

Item families come straight from the shipped paths:
  * weapons  - game/weapons/<class>/<name>/gun_*_mws_<name>_<rank>_merangedweaponblueprint
  * gear     - game/items/gear/...      (armor, helmets, chest/arms/legs, gear mods)
  * research - game/items/research/...  (augment materials, unlocks)
  * consumables / stackables
  * powers   - game/powers/<power>/...  (Ryder abilities, one per folder)

Run: python build_items.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ROOT / "data" / "asset-names.txt"
OUT = ROOT / "data" / "items.json"

WEAPON = re.compile(
    r"^game/weapons/([a-z]+)/([a-z0-9_]+)/gun_[a-z]+_mws_([a-z0-9_]+)_(\d+)_merangedweaponblueprint$",
    re.I)
POWER = re.compile(r"^game/powers/([a-z0-9_]+)/", re.I)
GEAR = re.compile(r"^game/items/gear/([a-z]+)/([a-z0-9_]+)", re.I)
RESEARCH = re.compile(r"^game/items/research/([a-z]+)/([a-z0-9_]+)", re.I)


def main() -> int:
    names = [ln.strip() for ln in NAMES.read_text(encoding="utf-8").splitlines() if ln.strip()]

    weapons: dict[str, dict] = {}
    for n in names:
        m = WEAPON.match(n)
        if not m:
            continue
        cls, folder, name, rank = m.group(1).lower(), m.group(2).lower(), m.group(3).lower(), int(m.group(4))
        w = weapons.setdefault(name, {"name": name, "class": cls, "folder": folder, "ranks": []})
        w["ranks"].append(rank)
    for w in weapons.values():
        w["ranks"] = sorted(set(w["ranks"]))

    gear: dict[str, set[str]] = defaultdict(set)
    research: dict[str, set[str]] = defaultdict(set)
    for n in names:
        g = GEAR.match(n)
        if g:
            gear[g.group(1)].add(g.group(2))
        r = RESEARCH.match(n)
        if r:
            research[r.group(1)].add(r.group(2))

    powers = sorted({m.group(1).lower() for n in names if (m := POWER.match(n))})

    consumables = sorted({n for n in names if n.lower().startswith("game/items/consumables/")})
    stackables = sorted({n for n in names if n.lower().startswith("game/items/stackables/")})

    data = {
        "source": "data/asset-names.txt",
        "weapons": sorted(weapons.values(), key=lambda w: (w["class"], w["name"])),
        "weapon_count": len(weapons),
        "weapon_variants": sum(len(w["ranks"]) for w in weapons.values()),
        "gear": {k: sorted(v) for k, v in sorted(gear.items())},
        "research": {k: sorted(v) for k, v in sorted(research.items())},
        "powers": powers,
        "consumables": consumables,
        "stackables": stackables,
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"  weapons: {data['weapon_count']} ({data['weapon_variants']} rank variants)")
    per_class = Counter(w["class"] for w in weapons.values())
    print(f"  by class: {dict(per_class)}")
    for cls in sorted(per_class):
        names_ = sorted(w["name"] for w in weapons.values() if w["class"] == cls)
        print(f"    {cls:14s} {', '.join(names_)}")
    print(f"  gear families: { {k: len(v) for k, v in data['gear'].items()} }")
    print(f"  research families: { {k: len(v) for k, v in data['research'].items()} }")
    print(f"  powers: {len(powers)}")
    print(f"  consumables: {len(consumables)}  stackables: {len(stackables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
