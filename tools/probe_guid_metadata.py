"""Look for save plot-flag GUIDs inside the game's .toc/.sb metadata.

If a flag GUID appears there, we can join names to GUIDs without decompressing cas data.
Scans every 16-byte window of the metadata files against the set of GUIDs from a save.
"""
from __future__ import annotations

import sys
from pathlib import Path

import profsave3 as p

GAME = Path(r"C:\Steam\steamapps\common\Mass Effect Andromeda")


def raw_guid(text: str) -> bytes:
    q = text.split("-")
    return (bytes.fromhex(q[0])[::-1] + bytes.fromhex(q[1])[::-1]
            + bytes.fromhex(q[2])[::-1] + bytes.fromhex(q[3]) + bytes.fromhex(q[4]))


def main() -> int:
    save = p.load(Path(sys.argv[1]))
    guid_map = {}
    for kind in ("bools", "ints", "floats", "transforms"):
        for g in save.plot.get(kind, {}):
            guid_map[raw_guid(g)] = (kind, g)
    print(f"tracking {len(guid_map)} GUIDs from {save.path.name}")

    files = sorted(GAME.rglob("*.toc")) + sorted(GAME.rglob("*.sb"))
    print(f"scanning {len(files)} metadata files "
          f"({sum(f.stat().st_size for f in files) / 1048576:.1f} MB)")

    total = 0
    per_file = {}
    for path in files:
        data = path.read_bytes()
        n = 0
        for i in range(0, len(data) - 15):
            if data[i:i + 16] in guid_map:
                n += 1
                if n <= 3:
                    kind, g = guid_map[data[i:i + 16]]
                    print(f"  {path.name} @0x{i:08X}  {g} ({kind})")
        if n:
            per_file[path.name] = n
            total += n
    print(f"total GUID occurrences in metadata: {total}")
    for name, n in sorted(per_file.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {name}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
