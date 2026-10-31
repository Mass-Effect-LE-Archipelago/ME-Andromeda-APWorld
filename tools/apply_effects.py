"""Batch item delivery into a save, with a backup.

Delivery is the last unbuilt half of the loop. The mechanism is proven here with a synthetic
effect set: several flag writes in one rewrite, a backup of the input, and a verification pass
that only the requested flags changed. Real item -> flag effects are still unknown (research
projects share their flags, and the player's inventory lives outside plot flags).

Usage:
  python apply_effects.py <save> <out-save> --ops ops.json [--backup-dir DIR]
  python apply_effects.py --selftest <save>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import profsave3 as p
import save_edit


def deliver(save_path: Path, out_path: Path, ops: list[dict], backup_dir: Path | None) -> list[str]:
    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / (save_path.name + ".backup")
        if not backup.exists():
            backup.write_bytes(save_path.read_bytes())
            print(f"backup: {backup}")

    before = p.load(save_path)
    log = save_edit.apply_batch(save_path, out_path, ops)
    after = p.load(out_path)

    changed = []
    for kind in ("bools", "ints", "floats"):
        a, b = before.plot.get(kind, {}), after.plot.get(kind, {})
        for guid in b:
            if a.get(guid) != b[guid]:
                changed.append((kind, guid, a.get(guid), b[guid]))
    expected = {(op["kind"] + "s", op["guid"]) for op in ops if op["kind"] in ("bool", "int", "float")}
    unexpected = [(k, g, x, y) for k, g, x, y in changed if (k, g) not in expected]
    if unexpected:
        raise SystemExit(f"{len(unexpected)} flag(s) changed that were not requested: {unexpected[:5]}")
    inserted = sum(1 for k, _g, x, _y in changed if k == "bools" and x is None)
    growth = out_path.stat().st_size - save_path.stat().st_size
    if growth != 16 * inserted:
        raise SystemExit(f"output grew {growth} bytes, expected {16 * inserted} for {inserted} inserted bool(s)")
    return log + [f"verified {len(changed)} changed flag(s) ({inserted} inserted, +{growth} bytes), CRCs recomputed"]


def selftest(save_path: Path) -> int:
    print(f"selftest on {save_path.name}")
    state = p.load(save_path)
    bools = list(state.plot["bools"].items())[:2]
    ints = list(state.plot["ints"].items())[:1]
    ops: list[dict] = []
    for guid, value in bools:
        ops.append({"kind": "bool", "guid": guid, "value": not value})
    for guid, value in ints:
        ops.append({"kind": "int", "guid": guid, "value": int(value) + 7})
    # An absent bool exercises the insert path (plot block grows, later positions move).
    ops.append({"kind": "bool", "guid": "00000000-0000-4000-8000-00000000a11e", "value": True})
    scratch = Path(__file__).resolve().parent / "scratch"
    scratch.mkdir(exist_ok=True)
    out = scratch / "effects-selftest.save"
    for line in deliver(save_path, out, ops, scratch / "backups"):
        print("  " + line)

    after = p.load(out)
    for op in ops:
        value = (after.plot["bools"].get(op["guid"]) if op["kind"] == "bool"
                 else after.plot["ints"].get(op["guid"]))
        if value != op["value"]:
            print(f"FAIL: {op['guid']} is {value}, expected {op['value']}")
            return 1
    print("SELFTEST PASSED: batch delivery verified on a real save")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("save", type=Path, nargs="?")
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("--ops", type=Path)
    ap.add_argument("--backup-dir", type=Path, default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        save = args.save or Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave"
        return selftest(save)
    if not (args.save and args.out and args.ops):
        ap.error("save, out and --ops are required unless --selftest is used")
    ops = json.loads(args.ops.read_text(encoding="utf-8"))["ops"]
    for line in deliver(args.save, args.out, ops, args.backup_dir):
        print("  " + line)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
