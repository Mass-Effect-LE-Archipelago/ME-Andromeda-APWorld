"""Trace the preloaded-bundle list entry by entry."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import profsave2 as p


def main() -> int:
    raw = Path(sys.argv[1]).read_bytes()
    hl, dl = struct.unpack_from("<II", raw, 10)
    ds = 18 + hl
    db = raw[ds + 4:ds + dl]
    r = p.BitReader(db, 0, len(db) * 8)
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
    print(f"prologue ok: flag={flag} ts={ts} name={name!r} gv={gv} sv={sv} u=({u1},{u2}) build={build}")
    print(f"pos after prologue {r.pos}")
    count = r.u16()
    print(f"bundle count field {count} at {r.pos - 16}")
    for i in range(count):
        field = r.pos
        raw_len = r.u16()
        chosen = None
        text = None
        for cand in (raw_len & 0x7FFF, raw_len & 0x7F, raw_len & 0xFF):
            if cand <= 0 or cand > 4000:
                continue
            save = r.pos
            b = r.bytes_(cand)
            if all(32 <= x < 127 for x in b):
                chosen = cand
                text = b
                break
            r.pos = save
        shown = repr(text[:60]) if text else "<fail>"
        print(f"{i:2d} field={field} raw={raw_len} chosen={chosen} end={r.pos} {shown}")
        if chosen is None:
            break
    print(f"final pos {r.pos} (byte {r.pos // 8}, phase {r.pos % 8})")
    print(f"next 32 bits = 0x{r.read(32):08X}")
    print(f"next 32 bits @-16 = 0x{r.read(16):04X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
