"""Summarise every save in the folder: where it is, when, and how far along."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"


def main() -> int:
    if not SAVE_DIR.exists():
        print("no save folder")
        return 1
    paths = sorted((f for f in SAVE_DIR.iterdir() if f.is_file() and f.name.startswith("Career")),
                   key=lambda f: f.stat().st_mtime)
    catalogue = None
    print(f"{'file':34s} {'timestamp':20s} {'flags':>7s}  where")
    for path in paths:
        try:
            save = p.load(path)
        except Exception as exc:  # noqa: BLE001
            print(f"{path.name:34s} FAILED: {exc}")
            continue
        flags = sum(len(save.plot.get(k, {})) for k in ("bools", "ints", "floats"))
        entry = save.header.get("entry1", "")
        print(f"{path.name:34s} {save.data.get('timestamp_iso', '?')[:19]:20s} {flags:7d}  {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
