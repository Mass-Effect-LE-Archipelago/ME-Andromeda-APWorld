"""Walk a full playthrough in order and report the named flags that flip at each step.

The `b191e387` career runs M0 -> M1 -> Nexus -> M2 -> Aya -> M3 -> Kadara -> M4 -> M5 -> Tempest ->
M7 -> Meridian -> Eos, so each step is a story boundary and the flips between steps are the
candidate unlock/objective flags.
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
OUT = ROOT / "docs" / "PROGRESSION-LADDER.md"


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c for c in catalogue}

    saves = []
    for name in LADDER:
        path = SAVE_DIR / name
        if not path.exists():
            print(f"missing {name}")
            continue
        save = p.load(path)
        saves.append((name, save, flags(save)))
        print(f"loaded {name:36s} {save.header.get('entry1', ''):18s} {len(saves[-1][2]):6d} flags")

    lines = ["# Progression ladder (career b191e387, one full playthrough)", ""]
    add = lines.append
    add("Saves in the order the game wrote them, with the named flags that flip between each pair.")
    add("")

    for i in range(1, len(saves)):
        prev_name, _, prev = saves[i - 1]
        name, save, cur = saves[i]
        add(f"## {prev_name} -> {name}   (`{save.header.get('entry1', '')}`, {len(cur)} flags)")
        add("")
        flips = [g for g, (kind, v) in cur.items()
                 if kind == "bools" and v is True and prev.get(g, ("bools", False))[1] is not True]
        named_flips = [named[g] for g in flips if g in named]
        add(f"{len(flips)} flags false -> true, {len(named_flips)} named")
        add("")
        for entry in sorted(named_flips, key=lambda c: (c["region"], c["name"]))[:60]:
            add(f"- `{entry['kind']}` **{entry['name']}**  — `{entry['best_source'][-60:]}`")
        add("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
