"""Decode the WorldMap agent (WorldMapSaveGameAgent, idx 2).

Layout (Gibbed + observation): u16 count, then per entry a 24-bit frame holding a 16-byte GUID,
a u16 inner count and inner records; a second list follows when the agent version is >= 4.

The GUIDs are the galaxy-map locations the player has discovered: 3 in the prologue, 4 after M1,
33 in the finished save.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402
from profsave3 import BitReader  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
FILES = ["Careerc8fa1bc8-Chapter0", "Careerc8fa1bc8-2AutoSave", "Careerc8fa1bc8-Mission",
         "Career870ee94-1ManualSave"]
WORLDMAP_INDEX = 2


def agent_payload(data_block: bytes, save, index: int):
    for agent in save.agents:
        if agent.index != index:
            continue
        for slot in (1, 3, 2, 4, 0):
            off = agent.offsets[slot]
            if off:
                sub = BitReader(data_block, off, len(data_block) * 8 - off)
                length = sub.u32(24)
                return sub.pos, length, agent.version
    raise SystemExit("no payload")


def read_list(r: BitReader) -> list[dict]:
    out = []
    count = r.u16()
    for _ in range(count):
        r.push_frame(24)
        guid = r.bytes_(16)
        inner = r.u16()
        out.append({"guid": guid.hex(), "inner": inner})
        r.pop_frame_lenient()
    return out


def main() -> int:
    joined = {}
    for src in ("docs/plot-flag-join.json", "tools/scratch/join-sweep.json"):
        path = ROOT / src
        if not path.exists():
            continue
        for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
            joined[asset["name"]] = asset

    for name in FILES:
        path = SAVE_DIR / name
        if not path.exists():
            continue
        save = p.load(path)
        _, data_block, _ = p.unwrap(path.read_bytes())
        start, length, version = agent_payload(data_block, save, WORLDMAP_INDEX)
        r = BitReader(data_block, start, length * 8)
        print(f"=== {name}  agent v{version}  payload {length} bits ===")
        try:
            first = read_list(r)
            second = read_list(r) if version >= 4 else []
        except Exception as exc:  # noqa: BLE001
            print(f"  decode failed: {exc}")
            continue
        print(f"  list1: {len(first)} entries   list2: {len(second)} entries")
        for entry in first[:6]:
            print(f"    {entry['guid']}  inner {entry['inner']}")
        for entry in second[:6]:
            print(f"    (l2) {entry['guid']}  inner {entry['inner']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
