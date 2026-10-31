"""PROFSAVE (MEA) reader — evidence-driven.

Container format (verified against a real 2017 MEA save):

    "FBCHUNKS"            u64  magic
    u16                   version
    u32                   header_length      (includes its own 4-byte checksum)
    u32                   data_length        (includes its own 4-byte checksum)
    header block          u32 crc32 + (header_length - 4) bytes
    data block            u32 crc32 + (data_length   - 4) bytes

    crc32 = standard reflected CRC-32 (poly 0xEDB88320) with initial value 0x12345678

Header block:

    "FBHEADER"  u16 version  u32 entry_count
    entry_count x { u32 hash, u16 length, length bytes }   (little endian)

Data block:

    "FB\\0SAVE\\n"         8 bytes
    then a MSB-first bit stream (fields are not byte aligned)

The bit stream stores values most-significant-bit first, and multi-byte integers are
byte-swapped on read (the engine wrote them little-endian into an MSB-first stream).
Strings are a u16 length followed by that many 8-bit characters.
"""
from __future__ import annotations

import argparse
import binascii
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

CHUNK_MAGIC = b"FBCHUNKS"
HEADER_MAGIC = b"FBHEADER"
SAVE_MAGIC = b"FB\x00SAVE\n"
CRC_SEED = 0x12345678
HEADER_ENTRY_COUNT = 19

# SaveHeader::EntryId order from the prior-art implementation. The on-disk order is
# independent of this; the hashes are what identify a value.
HEADER_ENTRY_NAMES = [
    "AreaNameStringId", "AreaThumbnailTextureId", "GameVersion", "RequiredDLC",
    "RequiredInstallGroup", "ProfileName", "ProfileUniqueName", "ProfileId", "LevelID",
    "PlayerLevel", "GameCompleted", "TrialMode", "CompletionPercentage", "DateTime",
    "LevelTitleID", "LevelFloorID", "LevelRegionID", "TotalPlaytime", "NameOverrideStringId",
]


def crc32_seeded(data: bytes, seed: int = CRC_SEED) -> int:
    """CRC-32 as the engine computes it: zlib semantics with a non-zero initial value."""
    return binascii.crc32(data, seed) & 0xFFFFFFFF


class BitReader:
    """MSB-first bit reader matching the engine's getbitbuffer semantics."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.bits = len(data) * 8

    def read(self, offset: int, nbits: int) -> int:
        if offset + nbits > self.bits:
            raise EOFError(f"read {nbits} bits at {offset} past end ({self.bits})")
        value = 0
        for i in range(nbits):
            pos = offset + i
            value = (value << 1) | ((self.data[pos >> 3] >> (7 - (pos & 7))) & 1)
        return value

    def read_bytes(self, offset: int, nbytes: int) -> bytes:
        return bytes(self.read(offset + 8 * i, 8) for i in range(nbytes))

    def read_u16(self, offset: int) -> int:
        return struct.unpack("<H", struct.pack(">H", self.read(offset, 16)))[0]

    def read_u32(self, offset: int) -> int:
        return struct.unpack("<I", struct.pack(">I", self.read(offset, 32)))[0]

    def read_u64(self, offset: int) -> int:
        return struct.unpack("<Q", struct.pack(">Q", self.read(offset, 64)))[0]


@dataclass
class HeaderEntry:
    index: int
    hash: int
    value: str
    name: str = ""


@dataclass
class ProfSave:
    path: Path
    version: int
    header_length: int
    data_length: int
    header_crc_ok: bool
    data_crc_ok: bool
    entries: list[HeaderEntry] = field(default_factory=list)
    data: bytes = b""
    # decoded data fields
    has_unknown: int = 0
    timestamp: int = 0
    save_name: str = ""
    game_version: int = 0
    save_version: int = 0
    unknown: tuple = ()
    user_build_info: int = 0
    level_name: str = ""
    level_unknown: int = 0
    preloaded_bundles: list[str] = field(default_factory=list)
    data_bit_end: int = 0

    def header_map(self) -> dict[str, str]:
        return {e.name or f"entry{e.index}": e.value for e in self.entries}


def parse_header(block: bytes) -> tuple[int, list[HeaderEntry]]:
    if block[:8] != HEADER_MAGIC:
        raise ValueError(f"bad header magic {block[:8]!r}")
    version, count = struct.unpack_from("<HI", block, 8)
    if count != HEADER_ENTRY_COUNT:
        raise ValueError(f"unexpected header entry count {count}")
    off = 14
    entries = []
    for i in range(count):
        h = struct.unpack_from("<I", block, off)[0]
        ln = struct.unpack_from("<H", block, off + 4)[0]
        val = block[off + 6:off + 6 + ln].decode("utf-8", "replace")
        off += 6 + ln
        entries.append(HeaderEntry(i, h, val, HEADER_ENTRY_NAMES[i] if i < len(HEADER_ENTRY_NAMES) else ""))
    return version, entries


def parse_data(data: bytes) -> dict:
    r = BitReader(data)
    out: dict = {}
    if r.read_bytes(0, 8) != SAVE_MAGIC:
        raise ValueError(f"bad save magic {r.read_bytes(0, 8)!r}")

    off = 64
    has_unknown = r.read(off, 4)
    off += 4
    out["has_unknown"] = has_unknown
    if has_unknown:
        off += 27
    out["timestamp"] = r.read_u32(off)
    off += 32

    def string(off: int) -> tuple[str, int]:
        ln = r.read_u16(off)
        off += 16
        if ln == 0:
            return "", off
        if ln > 4000:
            raise ValueError(f"implausible string length {ln} at bit {off - 16}")
        raw = r.read_bytes(off, ln)
        off += 8 * ln
        return raw.decode("utf-8", "replace"), off

    out["save_name"], off = string(off)
    out["game_version"] = r.read_u16(off); off += 16
    out["save_version"] = r.read_u16(off); off += 16
    u1 = r.read_u16(off); off += 16
    u2 = r.read_u16(off); off += 16
    out["unknown"] = (u1, u2)
    out["user_build_info"] = r.read_u32(off); off += 32
    out["level_name"], off = string(off)
    out["level_unknown"] = r.read_u32(off); off += 32

    count_raw = r.read_u16(off); off += 16
    count = count_raw & 0x7FFF
    out["bundle_count"] = count
    out["bundle_count_raw"] = count_raw
    bundles = []
    flags = []
    for _ in range(count):
        raw_len = r.read_u16(off); off += 16
        flags.append(raw_len >> 15)
        # Entry 0 of some saves carries 0x80 on top of the length (0xB7 for a
        # 55-character path). Try the plain value first; if the bytes are not text,
        # the flag bit is present, so mask it. A genuine path longer than 127 bytes
        # therefore still wins on the first candidate.
        chosen = None
        for candidate in (raw_len & 0x7FFF, raw_len & 0x7F, raw_len & 0xFF):
            if candidate in (0,) or candidate > 4000:
                continue
            probe = r.read_bytes(off, candidate)
            if all(32 <= x < 127 for x in probe):
                chosen = (candidate, probe)
                break
        if chosen is None:
            raise ValueError(f"unparseable bundle entry at bit {off - 16} (raw {raw_len})")
        ln, probe = chosen
        bundles.append(probe.decode("utf-8", "replace"))
        off += 8 * ln
    out["bundle_flags"] = flags
    out["preloaded_bundles"] = bundles
    out["bit_end"] = off
    return out


def load(path: Path) -> ProfSave:
    raw = path.read_bytes()
    if raw[:8] != CHUNK_MAGIC:
        raise ValueError(f"not a PROFSAVE (magic {raw[:8]!r})")
    version = struct.unpack_from("<H", raw, 8)[0]
    header_len, data_len = struct.unpack_from("<II", raw, 10)
    header_start = 18
    header_crc = struct.unpack_from("<I", raw, header_start)[0]
    header_block = raw[header_start + 4:header_start + header_len]
    data_start = header_start + header_len
    data_crc = struct.unpack_from("<I", raw, data_start)[0]
    data_block = raw[data_start + 4:data_start + data_len]

    header_crc_ok = crc32_seeded(header_block) == header_crc
    data_crc_ok = crc32_seeded(data_block) == data_crc

    hdr_version, entries = parse_header(header_block)
    save = ProfSave(path=path, version=version, header_length=header_len, data_length=data_len,
                    header_crc_ok=header_crc_ok, data_crc_ok=data_crc_ok, entries=entries, data=data_block)
    info = parse_data(data_block)
    save.has_unknown = info["has_unknown"]
    save.timestamp = info["timestamp"]
    save.save_name = info["save_name"]
    save.game_version = info["game_version"]
    save.save_version = info["save_version"]
    save.unknown = info["unknown"]
    save.user_build_info = info["user_build_info"]
    save.level_name = info["level_name"]
    save.level_unknown = info["level_unknown"]
    save.preloaded_bundles = info["preloaded_bundles"]
    save.data_bit_end = info["bit_end"]
    return save


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bundle-limit", type=int, default=12)
    args = ap.parse_args()

    s = load(args.path)
    if args.json:
        print(json.dumps({"version": s.version, "header_crc_ok": s.header_crc_ok, "data_crc_ok": s.data_crc_ok,
                          "header": s.header_map(), "save_name": s.save_name, "game_version": s.game_version,
                          "save_version": s.save_version, "timestamp": s.timestamp, "level_name": s.level_name,
                          "bundles": s.preloaded_bundles, "bit_end": s.data_bit_end}, indent=2))
        return 0

    print(f"file          {s.path.name}  ({s.path.stat().st_size} bytes)")
    print(f"container     version {s.version}  header {s.header_length}  data {s.data_length}")
    print(f"crc           header {'OK' if s.header_crc_ok else 'MISMATCH'}  data {'OK' if s.data_crc_ok else 'MISMATCH'}")
    print()
    print("header entries:")
    for e in s.entries:
        print(f"  [{e.index:2d}] 0x{e.hash:08X} {e.name:<24} {e.value[:100]!r}")
    print()
    print(f"data: has_unknown={s.has_unknown}  timestamp={s.timestamp}  save_name={s.save_name!r}")
    print(f"      game_version={s.game_version}  save_version={s.save_version}  unknown={s.unknown}  build={s.user_build_info}")
    print(f"      level_name={s.level_name!r}  level_unknown=0x{s.level_unknown:08X}")
    print(f"      preloaded_bundles={len(s.preloaded_bundles)} (first {args.bundle_limit}):")
    for b in s.preloaded_bundles[:args.bundle_limit]:
        print(f"        {b}")
    print(f"      stream position after header fields: {s.data_bit_end} bits ({s.data_bit_end // 8} bytes, "
          f"{s.data_bit_end % 8} bits into a byte)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
