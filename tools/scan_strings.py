"""Chain-scan a PROFSAVE body for length-prefixed strings, without assuming alignment.

For every bit offset, test: byteswapped u16 length in [1, maxlen] and the following
`length` bytes printable ASCII. On a hit, emit (offset, length, text) and jump past
the string; otherwise advance one bit. The gap between printable fields is printed as
`gap=N bits`, which is what reveals the field layout between strings.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import profsave as ps


def body(db: bytes) -> tuple[int, ps.BitReader]:
    r = ps.BitReader(db)
    off = 64
    hu = r.read(off, 4)
    off += 4
    if hu:
        off += 27
    off += 32

    def string(o: int) -> int:
        ln = r.read_u16(o)
        return o + 16 + 8 * ln

    off = string(off)
    off += 16 * 4 + 32
    off = string(off)
    off += 32
    count = r.read_u16(off)
    off += 16
    for _ in range(count):
        off = string(off)
    return off, r


def printable(b: bytes) -> bool:
    return all((32 <= x < 127) or x in (0, 9, 10, 13) for x in b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--start", type=lambda s: int(s, 0), default=None, help="bit offset (default: body start)")
    ap.add_argument("--span", type=lambda s: int(s, 0), default=64 * 1024, help="bytes to scan")
    ap.add_argument("--maxlen", type=int, default=400)
    ap.add_argument("--minlen", type=int, default=3)
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--raw", action="store_true", help="print full strings")
    args = ap.parse_args()

    raw = args.path.read_bytes()
    hl, dl = struct.unpack_from("<II", raw, 10)
    ds = 18 + hl
    db = raw[ds + 4:ds + dl]
    body_start, r = body(db)
    start = body_start if args.start is None else args.start
    end = min(r.bits, start + args.span * 8)
    print(f"body starts at bit {body_start} (byte {body_start // 8}, phase {body_start % 8}); scanning to bit {end}")

    o = start
    hits = 0
    gap_from = start
    while o < end:
        ln = r.read_u16(o)
        if args.minlen <= ln <= args.maxlen:
            try:
                b = r.read_bytes(o + 16, ln)
            except EOFError:
                break
            if printable(b):
                gap = o - gap_from
                txt = b.decode("utf-8", "replace")
                if not args.raw and len(txt) > 120:
                    txt = txt[:117] + "..."
                print(f"@{o:<9d} b{o // 8:<8d} ph{o % 8}  gap={gap:<5d} len={ln:<4d} {txt!r}")
                hits += 1
                o = o + 16 + 8 * ln
                gap_from = o
                if hits >= args.limit:
                    print("... limit reached")
                    return 0
                continue
        o += 1
    print(f"\n[hits={hits}, stopped at bit {o}, remaining gap={o - gap_from}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
