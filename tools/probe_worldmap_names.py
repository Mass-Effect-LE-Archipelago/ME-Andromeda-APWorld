"""Name the world-map entries: search space assets for the 33 location GUIDs.

Reads the GUIDs out of the WorldMap agent, then scans the raw (decompressed) partitions of every
`game/space/**` asset for those bytes. A hit tells us which asset defines/references the entry.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))
import profsave3 as p  # noqa: E402
from profsave3 import BitReader  # noqa: E402
from frostbite import vfs  # noqa: E402

SAVE = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave"


def world_map_guids() -> list[bytes]:
    save = p.load(SAVE)
    _, data, _ = p.unwrap(SAVE.read_bytes())
    for agent in save.agents:
        if agent.index != 2:
            continue
        sub = BitReader(data, agent.offsets[1], len(data) * 8 - agent.offsets[1])
        length = sub.u32(24)
        r = BitReader(data, sub.pos, length * 8)
        count = r.u16()
        out = []
        for _ in range(count):
            r.push_frame(24)
            out.append(r.bytes_(16))
            r.pop_frame_lenient()
        return out
    raise SystemExit("world map agent not found")


def main() -> int:
    guids = world_map_guids()
    print(f"world-map entries: {len(guids)}")
    for raw in guids[:3]:
        print(f"  {uuid.UUID(bytes_le=raw)}")

    game = vfs.Game()
    names = [n for n in game.iter_names("game/space/") if n.startswith("game/space/")]
    print(f"space assets to scan: {len(names)}")

    matches: dict[str, list[str]] = {}
    checked = 0
    for name in names:
        try:
            record = game.resolve(name)
            data, _ = game.chunk_data(record)
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        for raw in guids:
            if raw in data:
                matches.setdefault(name, []).append(str(uuid.UUID(bytes_le=raw)))
        if checked % 200 == 0:
            print(f"  ... {checked} scanned, {len(matches)} assets with hits", flush=True)

    print(f"\nscanned {checked} assets; {len(matches)} contain at least one entry")
    for name, hits in list(matches.items())[:20]:
        print(f"  {name}")
        for hit in hits[:4]:
            print(f"      {hit}")
    Path(ROOT / "docs" / "worldmap-guid-hits.json").write_text(
        json.dumps(matches, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
