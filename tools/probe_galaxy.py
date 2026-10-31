"""Decode the GalaxyDataManager save agent (galaxy map state).

Gibbed calls it `GalaxyDataStateManagerSaveAgent`; the agent table identifies agents by a
DJB2-XOR name hash, so we can find it without guessing indices.

Layout (version 2), verified against Gibbed's C#:
    u24 frame {
        u24 frame { guid current_system; guid current_destination }
        Unknown3: u24 frame { u32 count, [guid, u32]* ; u32 count, [guid, u32]* }
        Unknown4: same shape
    }
The (guid -> u32) maps are the galaxy state: destination/system GUIDs with a small state
value. This is where "which planets are unlocked" lives, not in the plot flags.

Usage: python probe_galaxy.py <save>
"""
from __future__ import annotations

import sys
from pathlib import Path

import profsave3 as p

AGENT_NAME = "GalaxyDataStateManagerSaveAgent"


def djb2x(text: str) -> int:
    h = 5381
    for c in text.encode():
        h = ((h * 33) ^ c) & 0xFFFFFFFF
    return h


def read_map(r: p.BitReader, version: int) -> dict[str, int]:
    out: dict[str, int] = {}
    if version >= 1:
        for _ in range(r.u32()):
            key = r.guid()
            out[key] = r.u32()
    return out


def read_unknown0(r: p.BitReader, version: int) -> tuple[dict[str, int], dict[str, int]]:
    r.push_frame(24)
    a = read_map(r, version)
    b = read_map(r, version)
    r.pop_frame()
    return a, b


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    header_block, data_block, info = p.unwrap(raw)
    save = p.load(path)

    target_hash = djb2x(AGENT_NAME)
    agent = next((a for a in save.agents if a.name_hash == target_hash), None)
    print(f"{path.name}: agent hash 0x{target_hash:08X} -> "
          f"{'idx ' + str(agent.index) if agent else 'NOT FOUND'}")
    if agent is None:
        return 1
    off = agent.offsets[1]
    if not off:
        print("no slot-1 payload")
        return 1

    r = p.BitReader(data_block, off, len(data_block) * 8 - off)
    outer_len = r.read(24)
    payload = r.pos
    print(f"payload at bit {payload} (outer frame {outer_len} bits)")

    r.push_frame(24)
    r.push_frame(24)
    current_system = r.guid()
    current_destination = r.guid()
    r.pop_frame()
    print(f"current_system      {current_system}")
    print(f"current_destination {current_destination}")
    u3a, u3b = read_unknown0(r, agent.version)
    u4a, u4b = read_unknown0(r, agent.version)
    r.pop_frame()
    print(f"unknown3: {len(u3a)} / {len(u3b)} entries")
    print(f"unknown4: {len(u4a)} / {len(u4b)} entries")
    for label, m in (("u3a", u3a), ("u3b", u3b), ("u4a", u4a), ("u4b", u4b)):
        if not m:
            continue
        values = {}
        for v in m.values():
            values[v] = values.get(v, 0) + 1
        print(f"  {label} value histogram: {dict(sorted(values.items())[:10])}")
        for k, v in list(m.items())[:5]:
            print(f"    {k} -> {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
