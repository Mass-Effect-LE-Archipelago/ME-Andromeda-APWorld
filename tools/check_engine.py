"""Check detection and item delivery engine for MEA.

This is the save-watch half of the client, independent of flag names:

  state   read the current flag values out of a save
  diff    turn "flag changed" into check events (guid, kind, before, after)
  deliver apply a list of item operations to a save copy (int add/set, float set, bool set)

Everything is keyed by GUID, so it works today; names attach later via the asset join.

Usage:
  python check_engine.py state   <save> [--out FILE]
  python check_engine.py diff    <old-save> <new-save> [--json]
  python check_engine.py deliver <save> <ops.json> <out-save>
  python check_engine.py selftest <save>

ops.json format: {"ops": [{"kind": "int", "guid": "...", "add": 5},
                          {"kind": "bool", "guid": "...", "value": true}]}
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import profsave3 as p
import save_edit


def read_state(path: Path) -> dict:
    save = p.load(path)
    plot = save.plot
    return {
        "save": path.name,
        "timestamp": save.data.get("timestamp_iso"),
        "bools": dict(plot.get("bools", {})),
        "ints": dict(plot.get("ints", {})),
        "floats": dict(plot.get("floats", {})),
    }


def diff(old: dict, new: dict) -> list[dict]:
    events = []
    ob, nb = old["bools"], new["bools"]
    for g, v in nb.items():
        if g in ob and ob[g] != v:
            events.append({"kind": "bool", "guid": g, "before": ob[g], "after": v})
    oi, ni = old["ints"], new["ints"]
    for g, v in ni.items():
        if g in oi and oi[g] != v:
            events.append({"kind": "int", "guid": g, "before": oi[g], "after": v})
    of, nf = old["floats"], new["floats"]
    for g, v in nf.items():
        if g in of and of[g] != v:
            events.append({"kind": "float", "guid": g, "before": of[g], "after": v})
    return events


def new_checks(old: dict, new: dict) -> list[str]:
    """Bools that went false -> true: the natural "check completed" signal."""
    return [e["guid"] for e in diff(old, new) if e["kind"] == "bool" and not e["before"] and e["after"]]


def deliver(save_path: Path, ops: list[dict], out_path: Path) -> list[str]:
    """Apply item operations. Returns human-readable log lines."""
    log: list[str] = []

    def mutate(plot):
        for op in ops:
            kind = op["kind"]
            guid = op["guid"]
            if kind == "int":
                cur = plot["ints"].get(guid)
                if cur is None:
                    log.append(f"SKIP int {guid}: not an int flag in this save")
                    continue
                if "set" in op:
                    plot["ints"][guid] = int(op["set"])
                    log.append(f"int {guid}: {cur} -> {op['set']}")
                else:
                    plot["ints"][guid] = cur + int(op.get("add", 0))
                    log.append(f"int {guid}: {cur} + {op.get('add', 0)} -> {plot['ints'][guid]}")
            elif kind == "float":
                cur = plot["floats"].get(guid)
                if cur is None:
                    log.append(f"SKIP float {guid}: not a float flag")
                    continue
                plot["floats"][guid] = float(op["value"])
                log.append(f"float {guid}: {cur} -> {op['value']}")
            elif kind == "bool":
                cur = plot["bools"].get(guid)
                if cur is None:
                    log.append(f"SKIP bool {guid}: not a bool flag")
                    continue
                plot["bools"][guid] = bool(op["value"])
                log.append(f"bool {guid}: {cur} -> {op['value']}")
            else:
                log.append(f"SKIP unknown op kind {kind!r}")

    save_edit.rewrite(save_path, out_path, mutate)
    return log


def selftest(save_path: Path) -> int:
    """Pick a real int flag, add 1 via deliver, re-read, and confirm everything else holds."""
    state = read_state(save_path)
    if not state["ints"]:
        print("no int flags to test")
        return 1
    guid, value = next(iter(state["ints"].items()))
    print(f"selftest flag {guid} = {value}")
    scratch = Path(__file__).resolve().parent / "scratch"
    scratch.mkdir(exist_ok=True)
    out = scratch / "selftest.save"
    log = deliver(save_path, [{"kind": "int", "guid": guid, "add": 1}], out)
    for line in log:
        print("  " + line)
    after = read_state(out)
    ok = True
    if after["ints"].get(guid) != value + 1:
        print(f"FAIL: int is {after['ints'].get(guid)}, expected {value + 1}")
        ok = False
    if len(after["bools"]) != len(state["bools"]):
        print("FAIL: bool count changed")
        ok = False
    mismatched = [g for g, v in state["bools"].items() if after["bools"].get(g) != v]
    if mismatched:
        print(f"FAIL: {len(mismatched)} bools changed unexpectedly")
        ok = False
    changed_ints = [g for g, v in state["ints"].items() if g != guid and after["ints"].get(g) != v]
    if changed_ints:
        print(f"FAIL: {len(changed_ints)} other ints changed")
        ok = False
    size_before = save_path.stat().st_size
    size_after = out.stat().st_size
    if size_before != size_after:
        print(f"FAIL: size {size_before} -> {size_after}")
        ok = False
    print("selftest PASS" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("state")
    s.add_argument("save", type=Path)
    s.add_argument("--out", type=Path)
    d = sub.add_parser("diff")
    d.add_argument("old", type=Path)
    d.add_argument("new", type=Path)
    d.add_argument("--json", action="store_true")
    dl = sub.add_parser("deliver")
    dl.add_argument("save", type=Path)
    dl.add_argument("ops", type=Path)
    dl.add_argument("out", type=Path)
    st = sub.add_parser("selftest")
    st.add_argument("save", type=Path)
    args = ap.parse_args()

    if args.cmd == "state":
        st = read_state(args.save)
        out = args.out or args.save.with_suffix(".state.json")
        out.write_text(json.dumps(st, indent=1))
        print(f"{args.save.name}: {len(st['bools'])} bools ({sum(st['bools'].values())} true), "
              f"{len(st['ints'])} ints, {len(st['floats'])} floats -> {out}")
    elif args.cmd == "diff":
        events = diff(read_state(args.old), read_state(args.new))
        checks = [e for e in events if e["kind"] == "bool" and not e["before"] and e["after"]]
        summary = {"total_events": len(events),
                   "new_bool_checks": len(checks),
                   "by_kind": {k: sum(1 for e in events if e["kind"] == k)
                               for k in ("bool", "int", "float")}}
        if args.json:
            summary["events"] = events[:500]
        print(json.dumps(summary, indent=1) if args.json else
              f"{summary['total_events']} events, {summary['new_bool_checks']} new bool checks, "
              f"{summary['by_kind']}")
    elif args.cmd == "deliver":
        ops = json.loads(args.ops.read_text())["ops"]
        for line in deliver(args.save, ops, args.out):
            print("  " + line)
        print(f"wrote {args.out}")
    elif args.cmd == "selftest":
        return selftest(args.save)
    return 0


if __name__ == "__main__":
    sys.exit(main())
