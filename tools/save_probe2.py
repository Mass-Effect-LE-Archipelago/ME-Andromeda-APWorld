"""Probe 2: test the 7-bit / bit-shift hypotheses on an MEA PROFSAVE.

Observations that motivate this:
  * header chunk "FBHEADER" is plain (u32 key hash + u16 len + ascii) records
  * immediately after it, text decodes cleanly as `stored_byte >> 1`
    (e.g. CE C2 DA CA -> "game"), i.e. the payload looks left-shifted by one bit
  * binary fields nearby (`62 00 00 00`, `32 00`) look unshifted

So: find where shifted data starts/ends, and whether a global bit offset (carry
across bytes) or a per-byte shift explains it.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path


def printable(b: bytes) -> bool:
    if not b:
        return False
    ok = sum(1 for x in b if 32 <= x < 127)
    return ok / len(b) > 0.95


def runs(b: bytes, limit: int = 40, minlen: int = 12) -> list[tuple[int, bytes]]:
    out = []
    for m in re.finditer(rb"[ -~]{%d,}" % minlen, b):
        out.append((m.start(), m.group()))
        if len(out) >= limit:
            break
    return out


def per_byte_shift(b: bytes) -> bytes:
    return bytes((x >> 1) for x in b)


def bit_shift(b: bytes, offset: int) -> bytes:
    """Right-shift the whole bitstream by `offset` bits (LSB-first carry)."""
    out = bytearray(len(b))
    carry = 0
    for i, x in enumerate(b):
        v = (x >> offset) | (carry << (8 - offset))
        carry = x & ((1 << offset) - 1)
        out[i] = v & 0xFF
    return bytes(out)


def score_text(b: bytes) -> float:
    """Fraction of bytes that look like lowercase-ASCII text or common punctuation."""
    if not b:
        return 0.0
    good = sum(1 for x in b if x in (0x20, 0x2F, 0x5F, 0x2D, 0x2E) or 0x61 <= x <= 0x7A or 0x41 <= x <= 0x5A or 0x30 <= x <= 0x39)
    return good / len(b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--tail", type=lambda s: int(s, 0), default=0x200)
    ap.add_argument("--start", type=lambda s: int(s, 0), default=0x1E1)
    ap.add_argument("--window", type=lambda s: int(s, 0), default=0x400)
    args = ap.parse_args()

    b = args.path.read_bytes()
    print(f"size 0x{len(b):X}")

    print("\n--- tail ---")
    for i in range(len(b) - args.tail, len(b), 16):
        row = b[i:i + 16]
        h = " ".join(f"{x:02X}" for x in row)
        a = "".join(chr(x) if 32 <= x < 127 else "." for x in row)
        print(f"{i:08X}  {h:<47}  {a}")

    print("\n--- global bit-shift scores (window after header) ---")
    win = b[args.start:args.start + args.window]
    for off in range(8):
        s = bit_shift(win, off+1) if False else (bit_shift(win, off) if off else win)
        print(f"offset {off}: score={score_text(s):.3f} first64={s[:64]!r}")

    print("\n--- per-byte >>1 sample ---")
    pb = per_byte_shift(win)
    print(pb[:200].decode("latin-1"))
    print()
    print("score per-byte>>1:", f"{score_text(pb):.3f}")

    print("\n--- text runs in whole file (raw) ---")
    rs = runs(b)
    for off, r in rs[:25]:
        print(f"0x{off:08X}  {r[:100].decode('latin-1')}")

    print("\n--- text runs in whole file (per-byte >>1) ---")
    sh = per_byte_shift(b)
    rs = runs(sh)
    for off, r in rs[:25]:
        print(f"0x{off:08X}  {r[:100].decode('latin-1')}")

    print("\n--- text runs in whole file (bit-shift 1) ---")
    sh = bit_shift(b, 1)
    rs = runs(sh)
    for off, r in rs[:15]:
        print(f"0x{off:08X}  {r[:100].decode('latin-1')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
