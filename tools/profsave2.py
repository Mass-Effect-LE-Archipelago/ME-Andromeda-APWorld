"""PROFSAVE reader v2 — full body parse, ported from Gibbed's MEA SaveFormats reference.

Container and prologue were verified directly against the owner's saves (see
docs/SAVE-FORMAT.md). The body grammar follows Gibbed's
`Gibbed.MassEffectAndromeda.SaveFormats` (zlib licence, Rick / gibbed), which
documents the frame-length bit stream, the per-subsystem "agents", and the plot
block keyed by GUIDs.

Key mechanics:
  * The whole data block is an MSB-first bit stream; multi-byte integers are stored
    little-endian and are byte-swapped on read.
  * A "frame" is `uN length` followed by that many bits of payload. Pop returns to
    frame start + length, so a mis-parse is detected at the next Pop.
  * Save subsystems live in "agents": a small header table (name hash, index,
    version) plus five optional payload slots per agent, referenced by bit offsets.
  * The plot agent's payload starts with a version, then the marker string
    "BioMetrics_PlotStartMarker", then GUID-keyed bool/int/float/transform sets.
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
PLOT_MARKER = "BioMetrics_PlotStartMarker"
CRC_SEED = 0x12345678
HEADER_ENTRY_COUNT = 19


class SaveFormatError(Exception):
    pass


class BitReader:
    """LSB-first bit reader, matching the engine's reader (Gibbed's BitReader).

    Within each byte, bit 0 is the least significant bit of the value, so a 16- or
    32-bit read at a byte-aligned position yields the little-endian integer directly.
    Strings are a u16 length followed by that many bytes, truncated at the first NUL.
    """

    def __init__(self, data: bytes, start_bit: int = 0, size_bits: int | None = None) -> None:
        self.data = data
        self.pos = start_bit
        self.size = start_bit + (size_bits if size_bits is not None else len(data) * 8 - start_bit)
        self._frames: list[tuple[int, int, str]] = []

    # -- primitives ---------------------------------------------------------
    def remaining(self) -> int:
        return self.size - self.pos

    def read(self, nbits: int) -> int:
        if nbits < 0:
            raise SaveFormatError(f"negative bit count {nbits}")
        if self.pos + nbits > self.size:
            raise SaveFormatError(f"read {nbits} bits at {self.pos} past end {self.size}")
        data = self.data
        result = 0
        shift = 0
        remaining = nbits
        while remaining > 0:
            offset = self.pos % 8
            left = min(8 - offset, remaining)
            mask = (1 << left) - 1
            value = data[self.pos >> 3] >> offset
            result |= (mask & value) << shift
            remaining -= left
            shift += left
            self.pos += left
        return result

    def skip(self, nbits: int) -> None:
        if nbits < 0:
            raise SaveFormatError(f"negative skip {nbits}")
        if self.pos + nbits > self.size:
            raise SaveFormatError(f"skip {nbits} at {self.pos} past end")
        self.pos += nbits

    def u8(self, nbits: int = 8) -> int:
        return self.read(nbits)

    def u16(self, nbits: int = 16) -> int:
        return self.read(nbits)

    def u32(self, nbits: int = 32) -> int:
        return self.read(nbits)

    def u64(self, nbits: int = 64) -> int:
        return self.read(nbits)

    def i32(self) -> int:
        v = self.u32()
        return v - (1 << 32) if v & 0x80000000 else v

    def f32(self) -> float:
        return struct.unpack("<f", struct.pack("<I", self.u32()))[0]

    def boolean(self) -> bool:
        return self.read(1) != 0

    def bytes_(self, n: int) -> bytes:
        return bytes(self.read(8) for _ in range(n))

    def guid(self) -> str:
        raw = self.bytes_(16)
        # .NET Guid(byte[]) uses mixed endianness for the first three fields; render
        # the canonical form so the value matches what the game logs.
        return (raw[3::-1].hex() + "-" + raw[5:3:-1].hex() + "-" + raw[7:5:-1].hex()
                + "-" + raw[8:10].hex() + "-" + raw[10:16].hex())

    def string(self) -> str:
        n = self.u16()
        if n > 4000:
            raise SaveFormatError(f"implausible string length {n} at bit {self.pos - 16}")
        raw = self.bytes_(n)
        zero = raw.find(b"\x00")
        if zero >= 0:
            raw = raw[:zero]
        return raw.decode("utf-8", "replace")

    # -- frames -------------------------------------------------------------
    def push_frame(self, nbits: int) -> int:
        value = self.read(nbits)
        self._frames.append((self.pos, value, "length"))
        return value

    def push_frame_position(self, nbits: int) -> int:
        value = self.read(nbits)
        self._frames.append((self.pos, value, "position"))
        return value

    def pop_frame(self) -> None:
        if not self._frames:
            raise SaveFormatError("frame stack underflow")
        start, value, kind = self._frames.pop()
        if kind == "length":
            end = start + value
            if end != self.pos:
                rel = "underrun" if self.pos < end else "overrun"
                raise SaveFormatError(f"frame {rel} of {abs(end - self.pos)} bits at {self.pos} (expected {end})")
        else:
            if value != self.pos:
                raise SaveFormatError(f"position frame {value} != current {self.pos}")

    @property
    def frame_depth(self) -> int:
        return len(self._frames)


def crc32_seeded(data: bytes, seed: int = CRC_SEED) -> int:
    return binascii.crc32(data, seed) & 0xFFFFFFFF


def unwrap(raw: bytes) -> tuple[bytes, bytes, dict]:
    """Split FBCHUNKS into header block and data block, verifying both CRCs."""
    if raw[:8] != CHUNK_MAGIC:
        raise SaveFormatError(f"not an FBCHUNKS file (magic {raw[:8]!r})")
    version = struct.unpack_from("<H", raw, 8)[0]
    header_len, data_len = struct.unpack_from("<II", raw, 10)
    hs = 18
    header_crc = struct.unpack_from("<I", raw, hs)[0]
    header_block = raw[hs + 4:hs + header_len]
    ds = hs + header_len
    data_crc = struct.unpack_from("<I", raw, ds)[0]
    data_block = raw[ds + 4:ds + data_len]
    if len(header_block) != header_len - 4 or len(data_block) != data_len - 4:
        raise SaveFormatError("truncated container")
    info = {
        "container_version": version,
        "header_length": header_len,
        "data_length": data_len,
        "header_crc_ok": crc32_seeded(header_block) == header_crc,
        "data_crc_ok": crc32_seeded(data_block) == data_crc,
    }
    return header_block, data_block, info


def parse_header(block: bytes) -> list[dict]:
    if block[:8] != HEADER_MAGIC:
        raise SaveFormatError(f"bad header magic {block[:8]!r}")
    version, count = struct.unpack_from("<HI", block, 8)
    if count != HEADER_ENTRY_COUNT:
        raise SaveFormatError(f"unexpected header entry count {count}")
    off = 14
    entries = []
    for i in range(count):
        h = struct.unpack_from("<I", block, off)[0]
        ln = struct.unpack_from("<H", block, off + 4)[0]
        val = block[off + 6:off + 6 + ln].decode("utf-8", "replace")
        off += 6 + ln
        entries.append({"index": i, "hash": h, "value": val})
    return entries


@dataclass
class Agent:
    index: int
    name_hash: int
    version: int
    offsets: list[int] = field(default_factory=lambda: [0] * 5)
    kind: str = "unknown"


@dataclass
class Save:
    path: Path
    info: dict
    header: dict[str, str]
    header_entries: list[dict]
    data: dict
    agents: list[Agent]
    plot: dict
    component_agents: list[dict]


def import_timestamp(value: int) -> str:
    import datetime
    seconds = value - 210866803200
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat()


def parse_plot(r: BitReader) -> dict:
    """Plot block. Called with the reader positioned at the agent payload start."""
    r.push_frame(24)
    version = r.u16()
    marker = ""
    if version >= 2:
        marker = r.string()
        if marker != PLOT_MARKER:
            raise SaveFormatError(f"plot marker {marker!r}")
    bools: dict[str, bool] = {}
    ints: dict[str, int] = {}
    floats: dict[str, float] = {}
    transforms: list[str] = []
    unknown: dict[int, str] = {}
    nbits = 31 if version >= 4 else 16
    if version >= 1:
        for _ in range(r.u32(nbits)):
            bools[r.guid()] = False
        for _ in range(r.u32(nbits)):
            bools[r.guid()] = True
        for _ in range(r.u16()):
            k = r.guid()
            ints[k] = r.i32()
        for _ in range(r.u16()):
            k = r.guid()
            floats[k] = r.f32()
        count = r.u16()
        for _ in range(count):
            transforms.append(r.guid())
            # Transform payload: unknown layout; the reference reads it but the
            # owners' saves are expected to have none. Fail loudly instead of
            # silently desynchronising.
            raise SaveFormatError("plot contains transforms; layout not implemented")
    if version >= 3:
        for _ in range(r.u16()):
            r.push_frame(24)
            k = r.u32()
            unknown[k] = r.guid()
            r.pop_frame()
    r.pop_frame()
    return {"version": version, "marker": marker, "bools": bools, "ints": ints,
            "floats": floats, "transforms": transforms, "unknown": unknown}


def parse_data(data_block: bytes) -> tuple[dict, list[Agent], dict, list[dict]]:
    r = BitReader(data_block, 0, len(data_block) * 8)
    if r.bytes_(8) != SAVE_MAGIC:
        raise SaveFormatError("bad save data signature")

    has_extra = r.read(4)
    if has_extra:
        r.skip(27)

    # 32-bit value here, then the save name. Gibbed's reference reads a 64-bit
    # timestamp, but on these saves only 63 bits sit between the magic and the name
    # length (verified: 4-bit flag + 27-bit skip + 32-bit value); a 64-bit read
    # lands on garbage. The value is not a Unix/ticks timestamp.
    timestamp = r.u32()
    save_file_name = r.string()
    game_version = r.u16()
    save_version = r.u16()
    unknown1 = r.u16()
    unknown2 = r.u16()
    user_build_info = r.u32()
    if game_version != 3:
        raise SaveFormatError(f"unsupported game version {game_version}")
    if not 20 <= save_version <= 22:
        raise SaveFormatError(f"unsupported save version {save_version}")

    level_name = r.string()
    unknown1b = r.u32()

    bundles = [r.string() for _ in range(r.u16())]
    layers = {}
    for _ in range(r.u16()):
        r.push_frame(24)
        layers[r.string()] = r.string()
        r.pop_frame()

    heaps = []
    for _ in range(r.u16(12)):
        r.push_frame(24)
        heap = {"name": r.string(), "u2": r.u32(), "u3": r.u32(), "type": r.u8(),
                "u4": r.u32(), "u5": r.boolean(), "u6": r.u8(), "u7": r.u8(), "u8": r.u32()}
        if save_version < 17:
            r.skip(1)
        heaps.append(heap)
        r.pop_frame()

    unknown2_list = []
    for _ in range(r.u16(12)):
        r.push_frame(24)
        unknown2_list.append({"u1": r.u16(), "u2": r.u16(), "u3": r.u8()})
        r.pop_frame()

    level_hash = r.guid()
    unknown5 = r.u32(20)
    if unknown5 != 0:
        r.skip(unknown5)

    unknown3 = r.u16()
    unknown4 = r.u16() if unknown3 >= 5 else 0
    unknown5b = r.boolean()

    component_data_position = r.u32(26)

    entity_bulk_length = r.u32()
    entity_bulk_position = r.pos
    r.skip(entity_bulk_length)

    unknown9 = r.pos
    r.push_frame(24 if save_version >= 18 else 6)
    r.push_frame(24)
    unknown6 = r.string()
    unknown7 = r.string()
    save_name = r.string()
    r.pop_frame()
    unknown8 = r.u32()
    unknown9g = r.guid()
    unknown10 = r.u32()
    r.pop_frame()

    unknown16 = r.u32(26)
    if unknown16 != unknown9:
        raise SaveFormatError(f"entity block position mismatch {unknown16} != {unknown9}")

    agent_bulk_length = r.u32()
    agent_bulk_position = r.pos
    r.skip(agent_bulk_length)

    agent_data_count = r.u8(4)
    lookup: dict[int, list[int]] = {}
    for _ in range(agent_data_count):
        index = r.u8()
        offsets = [r.u32(26) for _ in range(5)]
        for off in offsets:
            if off and not (agent_bulk_position <= off <= agent_bulk_position + agent_bulk_length):
                raise SaveFormatError(f"agent offset {off} outside bulk data")
        lookup[index] = offsets

    r.push_frame(24)
    entity_data_count = r.u16()
    entities = []
    for _ in range(entity_data_count):
        eid = r.u32()
        o0 = o1 = 0
        if r.boolean():
            o0 = r.u32(26)
        if r.boolean():
            o1 = r.u32(26)
        entities.append({"id": eid, "data0": o0, "data1": o1})

    unknown11 = [r.u32() for _ in range(r.u16())]
    unknown18_count = r.u16()
    if unknown18_count:
        raise SaveFormatError("unknown18 entries present; layout not implemented")
    unknown12 = [r.u32() for _ in range(r.u16())]
    r.pop_frame()

    r.push_frame(24)
    agent_count = r.u8(4)
    agents: list[Agent] = []
    for i in range(agent_count):
        name_hash = r.u32()
        index = r.u8()
        version = r.u16()
        agents.append(Agent(index=index, name_hash=name_hash, version=version,
                            offsets=lookup.get(index, [0] * 5)))
    r.pop_frame()

    if r.frame_depth != 0:
        raise SaveFormatError("unbalanced frames")
    if r.pos != component_data_position:
        raise SaveFormatError(f"agent block end {r.pos} != component block {component_data_position}")

    r.push_frame(32)
    unknown13 = r.u16()
    components = []
    if unknown13 == 1:
        for _ in range(r.u16()):
            r.push_frame(24)
            name_hash = r.u32()
            comp_version = r.u16()
            components.append({"name_hash": name_hash, "version": comp_version})
            r.pop_frame()
    r.pop_frame()

    # Agent payload slots. Slot 1 (index 1) is where the plot agent stores its data
    # (Agent.Read2). Identify the plot agent by its marker rather than by hash.
    plot = {}
    for slot in range(5):
        for agent in agents:
            off = agent.offsets[slot]
            if not off:
                continue
            sub = BitReader(data_block, off, len(data_block) * 8 - off)
            length = sub.u32(24)
            payload_start = sub.pos
            payload = bytes(_read_bits(data_block, payload_start, length))
            candidate = BitReader(payload, 0, length)
            if slot == 1:
                probe = BitReader(payload, 0, length)
                try:
                    candidate_plot = parse_plot(probe)
                    if candidate_plot["version"] >= 1:
                        plot = candidate_plot
                        agent.kind = "plot"
                except SaveFormatError:
                    pass

    info = {
        "timestamp": timestamp,
        "timestamp_iso": import_timestamp(timestamp) if timestamp > 210866803200 else None,
        "save_file_name": save_file_name,
        "game_version": game_version,
        "save_version": save_version,
        "unknown1": unknown1,
        "unknown2": unknown2,
        "user_build_info": user_build_info,
        "level_name": level_name,
        "level_hash": level_hash,
        "preloaded_bundles": bundles,
        "layer_inclusion": layers,
        "bundle_heaps": heaps,
        "entities": entities,
        "unknown3": unknown3,
        "unknown4": unknown4,
        "unknown5": unknown5b,
        "unknown6": unknown6,
        "unknown7": unknown7,
        "save_name": save_name,
        "unknown8": unknown8,
        "unknown9_guid": unknown9g,
        "unknown10": unknown10,
        "unknown11": unknown11,
        "unknown12": unknown12,
        "unknown13": unknown13,
        "component_data_position": component_data_position,
        "bits_total": len(data_block) * 8,
    }
    return info, agents, plot, components


def _read_bits(data: bytes, start: int, nbits: int) -> bytearray:
    out = bytearray((nbits + 7) // 8)
    for i in range(nbits):
        p = start + i
        if (data[p >> 3] >> (7 - (p & 7))) & 1:
            out[i >> 3] |= 1 << (7 - (i & 7))
    return out


def load(path: Path) -> Save:
    raw = path.read_bytes()
    header_block, data_block, info = unwrap(raw)
    entries = parse_header(header_block)
    data, agents, plot, components = parse_data(data_block)
    header = {f"entry{e['index']}": e["value"] for e in entries}
    return Save(path=path, info=info, header=header, header_entries=entries, data=data,
                agents=agents, plot=plot, component_agents=components)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--plot", type=int, default=0, help="print N plot entries per kind")
    args = ap.parse_args()

    try:
        s = load(args.path)
    except SaveFormatError as e:
        print(f"PARSE FAILED: {e}")
        return 2

    if args.json:
        print(json.dumps({"header": s.header, "data": s.data, "plot_counts": {
            k: len(v) for k, v in s.plot.items() if isinstance(v, dict)}, "agents": [
            {"index": a.index, "hash": a.name_hash, "version": a.version, "kind": a.kind,
             "offsets": a.offsets} for a in s.agents]}, indent=2, default=str))
        return 0

    print(f"{s.path.name}: container v{s.info['container_version']} "
          f"crc header={'ok' if s.info['header_crc_ok'] else 'BAD'} data={'ok' if s.info['data_crc_ok'] else 'BAD'}")
    d = s.data
    print(f"  save_name={d['save_file_name']!r} level={d['level_name']!r} build={d['user_build_info']}")
    print(f"  game/save version {d['game_version']}/{d['save_version']} unknown3={d['unknown3']} unknown4={d['unknown4']}")
    print(f"  timestamp raw={d['timestamp']} -> {d['timestamp_iso']}")
    print(f"  bundles={len(d['preloaded_bundles'])} layers={len(d['layer_inclusion'])} "
          f"heaps={len(d['bundle_heaps'])} entities={len(d['entities'])} components={len(s.component_agents)}")
    print(f"  agents={len(s.agents)}")
    for a in s.agents:
        used = [i for i, o in enumerate(a.offsets) if o]
        print(f"    idx {a.index:3d} hash 0x{a.name_hash:08X} v{a.version:<3d} {a.kind:<8s} slots={used}")
    p = s.plot
    if p:
        print(f"  PLOT v{p['version']} marker={p['marker']!r}")
        print(f"    bools={len(p['bools'])} (true={sum(p['bools'].values())}) ints={len(p['ints'])} "
              f"floats={len(p['floats'])} transforms={len(p['transforms'])} unknown={len(p['unknown'])}")
        if args.plot:
            for k, v in list(p["bools"].items())[:args.plot]:
                print(f"      bool {k} = {v}")
            for k, v in list(p["ints"].items())[:args.plot]:
                print(f"      int  {k} = {v}")
            for k, v in list(p["floats"].items())[:args.plot]:
                print(f"      flt  {k} = {v}")
    else:
        print("  PLOT not found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
