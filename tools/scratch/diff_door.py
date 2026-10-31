"""Diff the owner's early-Meridian exploration saves to find what the bridge door / final mission sets.

Usage: python diff_door.py <save A> <save B> [...]   (consecutive pairs are diffed)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profsave3 as p  # noqa: E402

D = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
J = json.loads((Path(__file__).resolve().parents[2] / "docs" / "plot-flag-join.json").read_text(encoding="utf-8"))
names = J["guid_to_names"]


def label(g):
    n = names.get(g)
    if not n:
        return ""
    return n[0] if isinstance(n, list) else str(n)


saves = [D / a for a in sys.argv[1:]]
loaded = [p.load(s) for s in saves]
for s, l in zip(saves, loaded):
    vals = [e["value"] for e in l.header_entries if e["value"] and len(e["value"]) < 60]
    print(f"{s.name}: bools={len(l.plot['bools'])} header={vals[:8]}")
for (sa, a), (sb, b) in zip(zip(saves, loaded), zip(saves[1:], loaded[1:])):
    ba, bb = a.plot["bools"], b.plot["bools"]
    became_true = [g for g, v in bb.items() if v and ba.get(g) is not True]
    became_false = [g for g, v in bb.items() if not v and ba.get(g) is True]
    named_t = [(g, label(g)) for g in became_true]
    named_f = [(g, label(g)) for g in became_false]
    ia, ib = a.plot["ints"], b.plot["ints"]
    ints = [(g, ia.get(g), v, label(g)) for g, v in ib.items() if ia.get(g) != v]
    print(f"\n== {sa.name} -> {sb.name}: +true {len(became_true)} ({len(named_t)} named), "
          f"true->false {len(became_false)} ({len(named_f)} named), named int changes {len(ints)}")
    for g, n in named_t:
        print(f"  T  {g}  {n}")
    for g, n in named_f:
        print(f"  F  {g}  {n}")
    for g, x, y, n in ints:
        print(f"  I  {g}  {x} -> {y}  {n}")

