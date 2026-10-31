"""Three-way diff across the prologue -> Eos boundary.

A = last prologue autosave (SavedGame_M0), B = first M1 save, C = later M1 save.
Flags that flip A->B and stay true in C are progression flags set by entering M1 (the Eos arc),
which is where a planet-access gate would live.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
A = SAVE_DIR / "Careerc8fa1bc8-2AutoSave"
B = SAVE_DIR / "Careerc8fa1bc8-Chapter1"
C = SAVE_DIR / "Careerc8fa1bc8-Mission"
JOINS = ["docs/plot-flag-join.json", "tools/scratch/join-sweep.json",
         "tools/scratch/join-conv.json", "tools/scratch/join-sweep2.json"]


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    a, b, c = p.load(A), p.load(B), p.load(C)
    fa, fb, fc = flags(a), flags(b), flags(c)
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {x["guid"]: x for x in catalogue}

    guides: dict[str, list[str]] = {}
    for src in JOINS:
        path = ROOT / src
        if not path.exists():
            continue
        for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
            for flag in asset.get("flags", []):
                guides.setdefault(flag["guid"], []).append(asset["name"])

    flipped = [g for g, (kind, v) in fb.items()
               if kind == "bools" and v is True and fa.get(g, ("bools", False))[1] is not True]
    sticky = [g for g in flipped if fc.get(g, ("bools", False))[1] is True]
    print(f"A {A.name}: {len(fa)} flags   B {B.name}: {len(fb)}   C {C.name}: {len(fc)}")
    print(f"A->B flips: {len(flipped)};  still true in C: {len(sticky)}")
    print(f"  named: {len([g for g in sticky if g in named])}")

    def describe(guid: str) -> str:
        entry = named.get(guid)
        source = entry["best_source"] if entry else (guides.get(guid) or ["(no asset)"])[0]
        label = entry["name"] if entry else "(unnamed)"
        return f"{label[:52]:52s} {source[-60:]}"

    print("\n-- sticky flips with a Meridian/Eos/Nexus/space source --")
    shown = 0
    for guid in sorted(sticky, key=describe):
        text = describe(guid)
        if any(t in text.lower() for t in ("eos", "space/", "destination", "hubs/hub_tempest", "m1", "planetside")):
            print(f"  {guid}  {text}")
            shown += 1
            if shown >= 40:
                break

    print("\n-- all sticky flips (first 40) --")
    for guid in sorted(sticky, key=describe)[:40]:
        print(f"  {guid}  {describe(guid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
