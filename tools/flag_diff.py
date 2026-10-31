"""Diff two saves and name the flags that changed.

Built for the moment an early/mid-game save arrives: comparing it against the 99.5% reference
should expose the progression flags (planet access, mission gates, the Meridian win) that two
finished playthroughs cannot.

Usage:
  python flag_diff.py <old-save> <new-save> [--join docs/plot-flag-join.json ...] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import profsave3 as p

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JOINS = [ROOT / "docs" / "plot-flag-join.json", ROOT / "tools" / "scratch" / "join-sweep.json"]


def load_names(paths: list[Path]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for path in paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for guid, value in data.get("guid_to_names", {}).items():
            bucket = names.setdefault(guid, set())
            if isinstance(value, str):
                bucket.add(value)
            else:
                bucket.update(value)
        for asset in data.get("assets", []):
            for flag in asset.get("flags", []):
                names.setdefault(flag["guid"], set()).add(asset["name"])
    return names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--join", action="append", default=None)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    joins = [Path(j) for j in args.join] if args.join else DEFAULT_JOINS
    names = load_names(joins)
    print(f"named flags available: {len(names)}")

    old = p.load(args.old)
    new = p.load(args.new)

    def compare(kind: str, label: str) -> None:
        a = old.plot.get(kind, {})
        b = new.plot.get(kind, {})
        became = sorted(g for g, v in b.items() if g in a and a[g] != v)
        only_new = sorted(set(b) - set(a))
        named = [g for g in became if g in names]
        print(f"\n{label}: {len(became)} changed, {len(only_new)} only in new, {len(named)} named")
        shown = 0
        for g in became:
            if g not in names:
                continue
            example = sorted(names[g])[0]
            print(f"  {g}  {a[g]} -> {b[g]}   {example}")
            shown += 1
            if shown >= args.limit:
                break

    compare("bools", "bools")
    compare("ints", "ints")
    compare("floats", "floats")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
