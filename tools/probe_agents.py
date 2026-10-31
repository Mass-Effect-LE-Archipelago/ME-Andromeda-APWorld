"""Dump every agent payload: index, name hash, slot, length and the first bytes.

The journal agent is the remaining place mission/planet state can live, so this maps the agent
block so its payload can be decoded next.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402
from profsave3 import BitReader  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
FILES = ["Careerc8fa1bc8-2AutoSave", "Careerc8fa1bc8-Mission", "Career870ee94-1ManualSave"]


def dump(path: Path) -> None:
    save = p.load(path)
    print(f"=== {path.name} ===")
    # re-parse to reach the agent block (the parser keeps agents but not payload offsets)
    raw = path.read_bytes()
    _, data_block, _ = p.unwrap(raw)
    info, agents, plot, components = p.parse_data(data_block)

    for agent in sorted(agents, key=lambda a: a.index):
        for slot, off in enumerate(agent.offsets):
            if not off:
                continue
            sub = BitReader(data_block, off, len(data_block) * 8 - off)
            length = sub.u32(24)
            start = sub.pos
            head = bytearray()
            probe = BitReader(data_block, start, min(length, 256))
            for _ in range(min(length, 256) // 8):
                head.append(probe.u8())
            print(f"  idx {agent.index:2d} hash 0x{agent.name_hash:08X} v{agent.version} "
                  f"slot {slot} off {off:8d} len {length:7d}  {bytes(head[:24]).hex(' ')}")
    print()


def main() -> int:
    for name in FILES:
        path = SAVE_DIR / name
        if path.exists():
            dump(path)
        else:
            print(f"missing {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
