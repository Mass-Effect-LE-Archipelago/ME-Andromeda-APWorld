"""Read-only probe for Mass Effect Andromeda PROFSAVE/FBCHUNKS files.

Usage:
  python save_probe.py <save-file> [--hex N] [--names] [--strings N]

This is a recon tool: it never writes to the save. It prints structure candidates
and string hits so the real parser can be written against evidence.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

CANDIDATE_CHUNK_NAMES = re.compile(rb"FB[A-Z0-9_]{3,31}")


def u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def hexdump(b: bytes, start: int, length: int) -> None:
    end = min(len(b), start + length)
    for i in range(start, end, 16):
        row = b[i:min(i + 16, end)]
        h = " ".join(f"{x:02X}" for x in row)
        a = "".join(chr(x) if 32 <= x < 127 else "." for x in row)
        print(f"{i:08X}  {h:<47}  {a}")


def chunk_name_offsets(b: bytes) -> list[tuple[int, bytes]]:
    hits = []
    for m in CANDIDATE_CHUNK_NAMES.finditer(b):
        hits.append((m.start(), m.group()))
    return hits


def read_header_records(b: bytes, start: int, count: int) -> list[tuple[int, str]]:
    recs = []
    o = start
    for _ in range(count):
        key = u32(b, o)
        o += 4
        ln = u16(b, o)
        o += 2
        val = b[o:o + ln].decode("utf-8", "replace")
        o += ln
        recs.append((key, val))
    return recs, o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--hex", type=lambda s: int(s, 0), default=0x300)
    ap.add_argument("--names", action="store_true")
    ap.add_argument("--strings", type=int, default=0)
    args = ap.parse_args()

    b = args.path.read_bytes()
    print(f"file   {args.path}")
    print(f"size   {len(b)} (0x{len(b):X})")
    print(f"magic  {b[:8]!r}")
    print()
    print("--- head ---")
    hexdump(b, 0, args.hex)
    print()

    if args.names:
        print("--- FB* name candidates ---")
        for off, name in chunk_name_offsets(b):
            print(f"0x{off:08X}  {name.decode('ascii', 'replace')}")
        print()

    # Candidate: FBCHUNKS header, u16 version @8, then a chunk record at 0x16
    print("--- front fields (little endian) ---")
    for o in (8, 10, 12, 14, 16, 18, 20):
        print(f"0x{o:02X}  u16=0x{u16(b, o):04X} ({u16(b, o)})   u32=0x{u32(b, o):08X} ({u32(b, o)})")
    print()

    print("--- try FBHEADER parse ---")
    hdr = b.find(b"FBHEADER")
    print(f"FBHEADER at 0x{hdr:08X}")
    if hdr > 0:
        ver = u16(b, hdr + 8)
        count = u32(b, hdr + 10)
        print(f"  after name: u16=0x{ver:04X}  u32=0x{count:08X} ({count})")
        if count < 1000:
            recs, end = read_header_records(b, hdr + 14, count)
            for k, v in recs:
                print(f"  key=0x{k:08X}  {v[:160]!r}")
            print(f"  header records end at 0x{end:08X}")
            print()
            print("--- bytes after header ---")
            hexdump(b, end, 0x200)
    print()

    if args.strings:
        print(f"--- printable strings >= {args.strings} chars (first 200) ---")
        n = 0
        for m in re.finditer(rb"[ -~]{%d,}" % args.strings, b):
            print(f"0x{m.start():08X}  {m.group()[:200].decode('ascii', 'replace')}")
            n += 1
            if n >= 200:
                print("... truncated at 200")
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
