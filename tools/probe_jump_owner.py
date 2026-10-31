"""Find the asset that owns the list of jumpable systems.

Collects the `JumpToSystem` GUIDs from system destination locators, then scans every space asset
for how many of them it references. The galaxy-map list asset should reference many.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import Partition  # noqa: E402

SYSTEMS = ["tools/scratch/sys_aya01.bin", "tools/scratch/sys_kadara.bin"]


def jump_guids() -> list[uuid.UUID]:
    found: list[uuid.UUID] = []
    for path in SYSTEMS:
        part = Partition((ROOT / path).read_bytes())
        for _name, obj in part.instance_objects():
            if isinstance(obj, dict) and "SystemDestinationLocator" in str(obj.get("$", "")):
                jump = obj.get("JumpToSystem") or {}
                text = jump.get("__import__") if isinstance(jump, dict) else None
                if text:
                    found.append(uuid.UUID(str(text)))
    return list(dict.fromkeys(found))


def patterns(g: uuid.UUID) -> list[bytes]:
    raw = g.bytes
    little = raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:]
    return [raw, little, raw[::-1]]


def main() -> int:
    guids = jump_guids()
    print(f"jump GUIDs collected: {len(guids)}")
    for g in guids:
        print("  ", g)
    pats = {g: patterns(g) for g in guids}

    game = vfs.Game()
    names = [n for n in game.iter_names("game/space/") if n.startswith("game/space/")]
    print(f"scanning {len(names)} space assets")
    scores: list[tuple[int, str, list[str]]] = []
    checked = 0
    for name in names:
        try:
            data, _ = game.chunk_data(game.resolve(name))
        except Exception:
            continue
        checked += 1
        hits = [str(g) for g, group in pats.items() if any(p in data for p in group)]
        if len(hits) >= 2:
            scores.append((len(hits), name, hits))
        if checked % 400 == 0:
            print(f"  ... {checked} scanned, {len(scores)} candidate(s)", flush=True)

    scores.sort(reverse=True)
    print(f"\nscanned {checked}; assets referencing 2+ jump GUIDs: {len(scores)}")
    for count, name, hits in scores[:15]:
        print(f"  {count:3d}  {name[:88]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
