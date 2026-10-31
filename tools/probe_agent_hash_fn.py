"""Calibrate the agent name hash: find which function and string produce 0x066D83C3.

We know idx 4 is the galaxy data agent (it stores current system/destination). Finding the exact
hash function lets all 13 agents be named, including the journal.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

TARGET = 0x066D83C3

BASES = ["GalaxyData", "GalaxyDataState", "GalaxyDataManager", "Galaxy", "GalaxyState",
         "GalaxyDataStateManager", "ME", "Me", "MEA"]
SUFFIXES = ["SaveAgent", "Agent", "SaveGameAgent", "SaveData", "SaveGameData", "Data", ""]


def fnv1a(text: str) -> int:
    h = 0x811C9DC5
    for ch in text.encode("utf-8"):
        h = ((h ^ ch) * 0x01000193) & 0xFFFFFFFF
    return h


def fnv1(text: str) -> int:
    h = 0x811C9DC5
    for ch in text.encode("utf-8"):
        h = ((h * 0x01000193) & 0xFFFFFFFF) ^ ch
    return h


def djb2_add(text: str) -> int:
    h = 5381
    for ch in text.encode("utf-8"):
        h = ((h * 33) + ch) & 0xFFFFFFFF
    return h


def djb2_xor(text: str) -> int:
    h = 5381
    for ch in text.encode("utf-8"):
        h = ((h * 33) ^ ch) & 0xFFFFFFFF
    return h


def sdbm(text: str) -> int:
    h = 0
    for ch in text.encode("utf-8"):
        h = (ch + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def crc32_hash(text: str) -> int:
    import zlib
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


HASHES = {"fnv1a": fnv1a, "fnv1": fnv1, "djb2_add": djb2_add, "djb2_xor": djb2_xor,
          "sdbm": sdbm, "crc32": crc32_hash}


def main() -> int:
    hits = 0
    for fn_name, fn in HASHES.items():
        for base, suffix in itertools.product(BASES, SUFFIXES):
            for case in (lambda s: s, lambda s: s.lower(), lambda s: s.upper()):
                name = case(base + suffix)
                if fn(name) == TARGET:
                    print(f"MATCH  {fn_name:9s} {name!r}")
                    hits += 1
    if not hits:
        print("no match; the hash is over a different string or uses a different function")
        # show what the known function produces for the obvious name, for reference
        for fn_name, fn in HASHES.items():
            print(f"  {fn_name:9s} 'GalaxyDataStateManagerSaveAgent' -> 0x{fn('GalaxyDataStateManagerSaveAgent'):08X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
