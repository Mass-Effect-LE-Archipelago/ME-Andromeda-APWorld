"""Which landable destinations reference the `alwaysfalse` condition, and how many times.

This is the target list for an "open the galaxy map" mod: each hit is a single GUID reference we
can swap for `alwaystrue` without changing any size or offset.
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

FALSE = uuid.UUID("c6660dbe-3614-11e5-aa63-b2e3b7222cc5")
CACHE = ROOT / "tools" / "scratch" / "dests"
CACHE.mkdir(parents=True, exist_ok=True)


def false_patterns() -> list[bytes]:
    raw = FALSE.bytes
    le = raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:]
    return [raw, le, raw[::-1]]


def main() -> int:
    names = [line.strip() for line in
             (ROOT / "data" / "asset-names.txt").read_text(encoding="utf-8").splitlines()]
    targets = sorted(n for n in names
                     if n.startswith("game/space/destinations/")
                     and ("destination_plt_" in n or "destination_lz_plt_" in n)
                     and n.count("/") == 4)
    print(f"landable destination assets: {len(targets)}")
    pats = false_patterns()
    rows = []
    for name in targets:
        leaf = name.rsplit("/", 1)[-1]
        out = CACHE / (leaf + ".bin")
        if not out.exists():
            result = subprocess.run([sys.executable, str(ROOT / "tools" / "frostbite" / "run.py"),
                                     "dump", name, "--out", str(out)], capture_output=True, text=True)
            if result.returncode != 0:
                rows.append((leaf, -1, "dump failed"))
                continue
        data = out.read_bytes()
        count = sum(data.count(p) for p in pats)
        rows.append((leaf, count, ""))

    for leaf, count, note in rows:
        if count == 0:
            status = "open? (no gate)"
        elif count > 0:
            status = f"{count} alwaysfalse ref(s)"
        else:
            status = note
        print(f"  {leaf:42s} {status}")
    gated = [r for r in rows if r[1] > 0]
    print(f"\nreferencing alwaysfalse: {len(gated)} of {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
