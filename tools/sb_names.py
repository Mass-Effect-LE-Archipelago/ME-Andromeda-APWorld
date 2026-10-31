"""Extract asset names from Frostbite superbundle metadata.

MEA's .sb files are DbObject records with plaintext fields:

    name \0 <len> <path>   sha1 \0 <20 bytes>   size \0 ...   originalSize \0 ...

The length byte often lands inside the preceding printable run, so names are recovered by
regex over printable runs and trimmed back to the path root. That gives the full asset-name
universe (millions of entries) without parsing cas data.

Modes:
  names <root> [--filter S] [--out FILE]   extract names
  plot <root>                              extract only plot-flag-looking names
  find <root> <guid>                       search .sb bytes for a save GUID
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RUN = re.compile(rb"[ -~]{4,400}")
ROOTS = ("game/", "Game/", "dev/", "Dev/", "engine/", "Engine/")


def extract(data: bytes):
    for m in RUN.finditer(data):
        s = m.group().decode("latin-1")
        cut = -1
        for root in ROOTS:
            idx = s.find(root)
            if idx >= 0 and (cut < 0 or idx < cut):
                cut = idx
        if cut < 0:
            continue
        name = s[cut:]
        # a trailing length byte of the *next* field can stick to the name; names never
        # contain control characters, so trimming non-path punctuation is enough
        name = name.rstrip("\x00")
        if "/" in name:
            yield name


def guid_bytes(text: str) -> bytes:
    parts = text.split("-")
    return (bytes.fromhex(parts[0])[::-1] + bytes.fromhex(parts[1])[::-1]
            + bytes.fromhex(parts[2])[::-1] + bytes.fromhex(parts[3]) + bytes.fromhex(parts[4]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["names", "plot", "find"])
    ap.add_argument("root", type=Path)
    ap.add_argument("guid", nargs="?")
    ap.add_argument("--filter", default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    files = sorted(set(args.root.rglob("*.sb")))
    print(f"{len(files)} .sb files under {args.root}")

    if args.mode == "find":
        needle = guid_bytes(args.guid)
        hits = 0
        for path in files:
            data = path.read_bytes()
            idx = data.find(needle)
            while idx >= 0:
                hits += 1
                print(f"  {path.name} @0x{idx:08X}")
                idx = data.find(needle, idx + 1)
        print(f"{hits} occurrence(s) of {args.guid}")
        return 0

    out = args.out.open("w", encoding="utf-8") if args.out else None
    seen: set[str] = set()
    shown = 0
    try:
        for path in files:
            data = path.read_bytes()
            for name in extract(data):
                if name in seen:
                    continue
                seen.add(name)
                is_plot = "/plots/" in name.lower() or "plotflag" in name.lower()
                if args.mode == "plot" and not is_plot:
                    continue
                if args.filter and args.filter not in name:
                    continue
                if out:
                    out.write(name + "\n")
                if shown < args.limit:
                    print("  " + name)
                    shown += 1
    finally:
        if out:
            out.close()
    plot_count = sum(1 for n in seen if "/plots/" in n.lower())
    print(f"unique names: {len(seen)}  (plot-looking: {plot_count})")
    if out:
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
