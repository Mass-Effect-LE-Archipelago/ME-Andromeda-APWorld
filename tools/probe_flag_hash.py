"""Test whether a plot flag's 16-byte GUID is derived from its asset name.

If it is, the 74k save GUIDs can be named offline. We have both halves:
  * ~1,148 plot asset names from the .sb metadata
  * 74,659 plot flag GUIDs from the 99.5% save

The test hashes each name with the plausible schemes and looks for a hit in the save's
GUID sets (all flags, true flags, and ints/floats).
"""
from __future__ import annotations

import binascii
import hashlib
import sys
from pathlib import Path

import profsave3 as p

GAME = Path(r"C:\Steam\steamapps\common\Mass Effect Andromeda")


def guid_raw(text: str) -> bytes:
    parts = text.split("-")
    return (bytes.fromhex(parts[0])[::-1] + bytes.fromhex(parts[1])[::-1]
            + bytes.fromhex(parts[2])[::-1] + bytes.fromhex(parts[3]) + bytes.fromhex(parts[4]))


def djb2x(s: str) -> int:
    h = 5381
    for c in s.encode():
        h = ((h * 33) ^ c) & 0xFFFFFFFF
    return h


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for c in s.encode():
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h


def main() -> int:
    save = p.load(Path(sys.argv[1]))
    plot = save.plot
    by_raw: dict[bytes, str] = {}
    for kind in ("bools", "ints", "floats"):
        for g in plot.get(kind, {}):
            by_raw[guid_raw(g)] = kind
    print(f"save flags: {len(by_raw)} ({sum(1 for v in by_raw.values() if v == 'bools')} bools)")

    names = [ln.strip() for ln in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"candidate plot names: {len(names)}")

    hits = 0
    checked = 0
    for name in names:
        checked += 1
        base = name.rsplit("/", 1)[-1]
        for text in (name, base):
            schemes = {
                "md5": hashlib.md5(text.encode()).digest(),
                "sha1[:16]": hashlib.sha1(text.encode()).digest()[:16],
                "sha256[:16]": hashlib.sha256(text.encode()).digest()[:16],
                "md5-le": hashlib.md5(text.encode()).digest()[::-1],
            }
            for label, raw in schemes.items():
                if raw in by_raw:
                    hits += 1
                    print(f"HIT {label}  {text}  -> {raw.hex()}")
            # 32-bit hash in the first four raw bytes
            for label, h in (("djb2x", djb2x(text)), ("fnv1a", fnv1a(text)),
                             ("crc32", binascii.crc32(text.encode()) & 0xFFFFFFFF)):
                prefix = h.to_bytes(4, "little")
                for candidate in by_raw:
                    if candidate[:4] == prefix:
                        hits += 1
                        print(f"HIT {label}-prefix {text} h=0x{h:08X} -> {candidate.hex()}")
                        break
    print(f"checked {checked} names, {hits} hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
