"""Brute-force the save data prologue field widths.

Gibbed's reference reads: u64 magic, 1-bit bool, optional 27-bit skip, u64 timestamp,
string save name, u16 game version ... Our earlier reads matched the strings with
different widths, so find the combination that reproduces every known-good field:
the save name, game version 3, save version 22, and the (10, 0) pair.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import profsave2 as p2


def probe(data: bytes, flag_bits: int, skip_bits: int, ts_bits: int) -> dict | None:
    r = p2.BitReader(data, 0, len(data) * 8)
    try:
        if r.bytes_(8) != p2.SAVE_MAGIC:
            return None
        flag = r.read(flag_bits) if flag_bits else 0
        if flag:
            r.skip(skip_bits)
        ts = r.read(ts_bits)
        name = r.string()
        gv = r.u16()
        sv = r.u16()
        u1 = r.u16()
        u2 = r.u16()
        build = r.u32()
        if build > 0x7FFFFFFF:
            return None
        level = r.string()
        return {"flag_bits": flag_bits, "skip": skip_bits, "ts_bits": ts_bits, "flag": flag,
                "ts": ts, "name": name, "gv": gv, "sv": sv, "u": (u1, u2), "build": build,
                "level": level, "ts_swapped": int.from_bytes(ts.to_bytes(ts_bits // 8, "big"), "little")}
    except p2.SaveFormatError:
        return None


def main() -> int:
    data = Path(sys.argv[1]).read_bytes()
    hl, dl = struct.unpack_from("<II", data, 10)
    ds = 18 + hl
    block = data[ds + 4:ds + dl]
    good = []
    for flag_bits in (1, 4, 8):
        for skip in (0, 27, 28, 31):
            for ts_bits in (32, 64):
                out = probe(block, flag_bits, skip, ts_bits)
                if not out:
                    continue
                ok = (out["gv"] == 3 and out["sv"] in (20, 21, 22) and out["u"] == (10, 0)
                      and out["name"].startswith("Career") and 1 <= out["build"] < 100_000_000)
                mark = "  <== MATCH" if ok else ""
                print(f"flag={flag_bits:2d} skip={skip:2d} ts={ts_bits:2d} -> flag={out['flag']:#x} "
                      f"name={out['name'][:40]!r} gv={out['gv']} sv={out['sv']} u={out['u']} "
                      f"build={out['build']} ts={out['ts']} sw={out['ts_swapped']}{mark}")
                if ok:
                    good.append(out)
    print()
    print(f"{len(good)} matching combination(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
