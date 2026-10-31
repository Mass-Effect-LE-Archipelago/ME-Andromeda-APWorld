"""Scan Frostbite .sb files for embedded ASCII strings of interest.

Superbundles are up to hundreds of MB but small compared with the 43 GB of cas data, and
if asset or type names survive anywhere in the shipped metadata they will be here
(and in initfs/layout.toc). Streams the files so memory stays flat.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PRINTABLE = re.compile(rb"[ -~]{4,200}")
DEFAULT_NEEDLES = [b"plot", b"Plot", b"PLOT"]


def scan(path: Path, needles: list[bytes], limit: int, context: int = 0) -> None:
    size = path.stat().st_size
    done = 0
    found = 0
    with path.open("rb") as fh:
        overlap = b""
        while done < size and found < limit:
            block = fh.read(4 * 1024 * 1024)
            if not block:
                break
            data = overlap + block
            for m in PRINTABLE.finditer(data):
                s = m.group()
                if any(n in s for n in needles):
                    abs_off = done - len(overlap) + m.start()
                    print(f"{path.name} @0x{abs_off:08X}  {s[:160].decode('latin-1')}")
                    found += 1
                    if found >= limit:
                        break
            overlap = data[-256:]
            done += len(block)
    print(f"-- {path.name}: {found} hits (scanned {done} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--needle", action="append", default=None)
    ap.add_argument("--max-bytes", type=lambda s: int(s, 0), default=64 * 1024 * 1024,
                    help="skip files larger than this")
    args = ap.parse_args()
    needles = [n.encode() for n in args.needle] if args.needle else DEFAULT_NEEDLES

    files = sorted(args.root.rglob("*.sb")) + sorted(args.root.rglob("*.toc"))
    print(f"{len(files)} candidate files")
    for path in files:
        if path.stat().st_size > args.max_bytes:
            continue
        scan(path, needles, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
