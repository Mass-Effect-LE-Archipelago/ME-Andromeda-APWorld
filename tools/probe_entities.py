"""Dump the entity section: entities, their data offsets, and the bytes they point at.

The player's inventory/research is not in plot flags, so the entity bulk data is the next place
to look. This prints structure only; interpretation comes after.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profsave3 as p  # noqa: E402

SAVES = {
    "99.5%": "Career870ee94-1ManualSave",
    "87.4%": "Careered8233e3-0ManualSave",
}
SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"


def hexdump(data: bytes, offset: int = 0, length: int = 96) -> str:
    chunk = data[offset:offset + length]
    rows = []
    for i in range(0, len(chunk), 16):
        part = chunk[i:i + 16]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in part)
        rows.append(f"    {offset + i:04x}  {part.hex(' '):47s}  {text}")
    return "\n".join(rows)


def main() -> int:
    for label, name in SAVES.items():
        path = SAVE_DIR / name
        if not path.exists():
            print(f"{label}: missing {path}")
            continue
        save = p.load(path)
        print(f"=== {label} ({name}) ===")
        print(f"  entities: {len(save.entities)}")
        for entity in save.entities[:4]:
            print(f"    id={entity['id']} data0={entity['data0']} data1={entity['data1']}")
        bulk = getattr(save, "entity_bulk", None)
        print(f"  entity bulk length: {len(bulk) if bulk is not None else 'not captured'}")
        if bulk:
            for entity in save.entities[:2]:
                for key in ("data0", "data1"):
                    off = entity[key]
                    if off:
                        print(f"    {key} @{off}:")
                        print(hexdump(bulk, off))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
