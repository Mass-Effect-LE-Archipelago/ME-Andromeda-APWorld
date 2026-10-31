"""Dump and diff MEA plot flags.

`dump`  writes every plot entry of a save to JSON.
`diff`  reports which bool flags flipped (and which ints/floats changed) between two
        saves. This is the basis for turning game activity into Archipelago checks:
        a flag that goes false -> true during play is an observable event.

Flag keys are the GUIDs the engine stores; mapping them to human names needs the
game's plot database (open item).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import profsave3 as p


def dump(path: Path) -> dict:
    save = p.load(path)
    plot = save.plot
    return {
        "save": path.name,
        "save_name": save.data["save_file_name"],
        "timestamp": save.data["timestamp_iso"],
        "build": save.data["user_build_info"],
        "plot_version": plot.get("version"),
        "bools": plot.get("bools", {}),
        "ints": plot.get("ints", {}),
        "floats": plot.get("floats", {}),
        "transforms": {k: list(v) for k, v in plot.get("transforms", {}).items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("save", type=Path)
    d.add_argument("--out", type=Path, default=None)
    df = sub.add_parser("diff")
    df.add_argument("a", type=Path)
    df.add_argument("b", type=Path)
    df.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "dump":
        data = dump(args.save)
        out = args.out or (args.save.with_suffix(".plot.json"))
        out.write_text(json.dumps(data, indent=1, sort_keys=True))
        print(f"{args.save.name}: {len(data['bools'])} bools ({sum(data['bools'].values())} true), "
              f"{len(data['ints'])} ints, {len(data['floats'])} floats -> {out}")
        return 0

    a, b = dump(args.a), dump(args.b)
    ab, bb = a["bools"], b["bools"]
    common = set(ab) & set(bb)
    became_true = sorted(k for k in common if not ab[k] and bb[k])
    became_false = sorted(k for k in common if ab[k] and not bb[k])
    only_a = sorted(set(ab) - set(bb))
    only_b = sorted(set(bb) - set(ab))
    ai, bi = a["ints"], b["ints"]
    int_changed = sorted(k for k in set(ai) & set(bi) if ai[k] != bi[k])
    int_only_b = sorted(set(bi) - set(ai))
    af, bf = a["floats"], b["floats"]
    float_changed = sorted(k for k in set(af) & set(bf) if af[k] != bf[k])

    summary = {
        "a": a["save_name"], "b": b["save_name"],
        "bools": {"became_true": len(became_true), "became_false": len(became_false),
                  "only_a": len(only_a), "only_b": len(only_b)},
        "ints": {"changed": len(int_changed), "only_b": len(int_only_b)},
        "floats": {"changed": len(float_changed)},
    }
    if args.json:
        summary["detail"] = {"became_true": became_true[:200], "became_false": became_false[:200],
                             "int_changed": int_changed[:200]}
        print(json.dumps(summary, indent=1))
        return 0

    print(f"A {a['save_name']} -> B {b['save_name']}")
    print(f"  bools: {summary['bools']}")
    print(f"  ints : {summary['ints']}")
    print(f"  floats: {summary['floats']}")
    for k in became_true[:10]:
        print(f"    + true  {k}")
    for k in became_false[:5]:
        print(f"    - false {k}")
    for k in int_changed[:5]:
        print(f"    ~ int   {k}: {ai[k]} -> {bi[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
