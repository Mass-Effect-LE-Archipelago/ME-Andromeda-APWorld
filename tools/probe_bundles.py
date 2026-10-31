"""Walk the MEA prologue bundle list entry by entry, with per-entry diagnostics.

Usage: python probe_bundles.py <save> [--count-offset N]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import profsave as ps


def prologue(r: ps.BitReader) -> tuple[int, dict]:
    off = 64
    hu = r.read(off, 4)
    off += 4
    if hu:
        off += 27
    ts = r.read_u32(off)
    off += 32

    def s(o: int):
        ln = r.read_u16(o)
        o += 16
        return r.read_bytes(o, ln).decode("utf-8", "replace"), o + 8 * ln

    name, off = s(off)
    gv = r.read_u16(off); off += 16
    sv = r.read_u16(off); off += 16
    u1 = r.read_u16(off); off += 16
    u2 = r.read_u16(off); off += 16
    build = r.read_u32(off); off += 32
    level, off = s(off)
    lu = r.read_u32(off); off += 32
    return off, dict(hu=hu, ts=ts, name=name, gv=gv, sv=sv, u=(u1, u2), build=build, level=level, lu=lu)


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    hl, dl = struct.unpack_from("<II", raw, 10)
    ds = 18 + hl
    db = raw[ds + 4:ds + dl]
    r = ps.BitReader(db)

    off, info = prologue(r)
    count = r.read_u16(off) & 0x7FFF
    print(f"prologue: {info}")
    print(f"count field at {off} -> {count}; entries start at {off + 16}")
    off += 16
    for i in range(count):
        field = off
        raw_len = r.read_u16(off); off += 16
        cands = []
        for c in (raw_len & 0x7FFF, raw_len & 0x7F, raw_len & 0xFF, raw_len - 128 if raw_len > 128 else raw_len):
            b = r.read_bytes(off, c) if 0 < c < 4000 else b""
            cands.append((c, all(32 <= x < 127 for x in b), b[:40]))
        print(f"[{i:2d}] field@{field} raw={raw_len}  " + " | ".join(
            f"{c}{'OK' if ok else '--'}:{b!r}" for c, ok, b in cands))
        pick = next(((c, ok, b) for c, ok, b in cands if ok), None)
        if pick is None:
            print("   -> no printable candidate; stopping")
            break
        c, ok, _ = pick
        off += 8 * c
    print(f"list would end at bit {off} (byte {off // 8}, phase {off % 8})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
