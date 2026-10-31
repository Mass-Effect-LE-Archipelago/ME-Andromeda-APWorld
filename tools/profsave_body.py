"""Inspect the body of an MEA PROFSAVE after the prologue fields.

The body is a bit stream, so text is usually *not* byte aligned. This tool maps
which bit phase (`offset % 8`) holds readable text at each point, which is how we
discover the record layout empirically.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import profsave as ps


def read_prologue(db: bytes):
    r = ps.BitReader(db)
    off = 64
    hu = r.read(off, 4)
    off += 4
    if hu:
        off += 27
    ts = r.read_u32(off)
    off += 32

    def string(off: int):
        ln = r.read_u16(off)
        off += 16
        raw = r.read_bytes(off, ln) if ln else b""
        return raw.decode("utf-8", "replace"), off + 8 * ln

    name, off = string(off)
    game_version = r.read_u16(off); off += 16
    save_version = r.read_u16(off); off += 16
    u1 = r.read_u16(off); off += 16
    u2 = r.read_u16(off); off += 16
    build = r.read_u32(off); off += 32
    level, off = string(off)
    level_unknown = r.read_u32(off); off += 32
    count = r.read_u16(off); off += 16
    bundles = []
    for _ in range(count):
        b, off = string(off)
        bundles.append(b)
    return dict(timestamp=ts, save_name=name, game_version=game_version, save_version=save_version,
                unknown=(u1, u2), build=build, level=level, level_unknown=level_unknown,
                bundles=bundles, body_start=off), r


def text_at(r: ps.BitReader, bit: int, maxlen: int = 200) -> str:
    """Best-effort: read bytes assuming byte alignment relative to `bit` phase."""
    out = []
    for i in range(maxlen):
        # read 8 bits starting at bit + 8*i (the reader is phase-agnostic)
        try:
            v = r.read(bit + 8 * i, 8)
        except EOFError:
            break
        if v == 0:
            break
        if 32 <= v < 127:
            out.append(chr(v))
        else:
            break
    return "".join(out)


def scan_phases(r: ps.BitReader, start_bit: int, window_bytes: int) -> None:
    """For each bit phase, report text runs and where they start."""
    for phase in range(8):
        runs = []
        bit = ((start_bit + 7) // 8) * 8 + phase
        cur = []
        cur_start = None
        end = start_bit + window_bytes * 8
        while bit < end:
            s = text_at(r, bit, min(64, (end - bit) // 8))
            if len(s) >= 8:
                runs.append((bit, s))
                bit += 8 * max(1, len(s))
            else:
                bit += 8
        if runs:
            print(f"  phase {phase}: {len(runs)} runs")
            for b, s in runs[:12]:
                print(f"    @{b:<9d} (byte {b // 8:<8d}) {s}")


def dump_region(db: bytes, start_bit: int, nbytes: int) -> None:
    begin = start_bit // 8
    end = min(len(db), begin + nbytes)
    for i in range(begin, end, 16):
        row = db[i:min(i + 16, end)]
        h = " ".join(f"{x:02X}" for x in row)
        a = "".join(chr(x) if 32 <= x < 127 else "." for x in row)
        print(f"{i:08X}  {h:<47}  {a}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--window", type=int, default=3072)
    ap.add_argument("--dump", type=int, default=0)
    args = ap.parse_args()

    raw = args.path.read_bytes()
    version = struct.unpack_from("<H", raw, 8)[0]
    hl, dl = struct.unpack_from("<II", raw, 10)
    ds = 18 + hl
    db = raw[ds + 4:ds + dl]
    info, r = read_prologue(db)

    print(f"game_version={info['game_version']} save_version={info['save_version']} "
          f"unknown={info['unknown']} build={info['build']} level={info['level']!r}")
    print(f"bundles ({len(info['bundles'])}):")
    for b in info["bundles"]:
        print(f"  {b}")
    start = info["body_start"]
    print(f"body starts at bit {start} (byte {start // 8}, phase {start % 8})")
    print()

    if args.dump:
        print("--- raw region from body start ---")
        dump_region(db, start, args.dump)
        print()

    print(f"--- text runs by phase in the next {args.window} bytes ---")
    scan_phases(r, start, args.window)
    return 0


if __name__ == "__main__":
    sys.exit(main())
