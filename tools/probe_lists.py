"""After the 26 preloaded bundles: check whether another string list follows."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import profsave2 as p


def prologue(r: p.BitReader):
    r.bytes_(8)
    flag = r.read(4)
    if flag:
        r.skip(27)
    ts = r.u32()
    name = r.string()
    gv, sv, u1, u2 = r.u16(), r.u16(), r.u16(), r.u16()
    build = r.u32()
    level = r.string()
    unknown = r.u32()
    return dict(ts=ts, name=name, gv=gv, sv=sv, u=(u1, u2), build=build, level=level, unknown=unknown)


def string_list(r: p.BitReader, count: int) -> list[str]:
    out = []
    for _ in range(count):
        out.append(r.string())
    return out


def main() -> int:
    raw = Path(sys.argv[1]).read_bytes()
    hl, dl = struct.unpack_from("<II", raw, 10)
    ds = 18 + hl
    db = raw[ds + 4:ds + dl]
    r = p.BitReader(db, 0, len(db) * 8)
    info = prologue(r)
    print("prologue:", info, "pos", r.pos)
    first = r.u16()
    names = string_list(r, first)
    print(f"list1 count={first} pos={r.pos} last={names[-1]!r}")
    second = r.u16()
    print(f"next u16 at {r.pos - 16} = {second}")
    names2 = string_list(r, second)
    print(f"list2 count={second} pos={r.pos} last={names2[-1]!r}")
    print(f"next u16 = {r.u16()} at {r.pos - 16}")
    print(f"next 32 bits = 0x{r.read(32):08X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
