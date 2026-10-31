"""Did the game actually load our patched systemdata chunks?

Reads Frosty's applied overlay (ModData/Default/patch/win32/galaxysystemcontent.sb) and compares
every systemdata_* entry against the vanilla .sb: if the sha1 differs, the overlay points at the
mod chunk.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))
from frostbite import dbobject, filelayer  # noqa: E402

GAME = Path(r"C:\Steam\steamapps\common\Mass Effect Andromeda")
OVERLAY_SB = GAME / "ModData" / "Default" / "patch" / "win32" / "galaxysystemcontent.sb"
VANILLA_SB = GAME / "Patch" / "Win32" / "galaxysystemcontent.sb"


def entries(path: Path) -> dict[str, tuple[bytes, int]]:
    body, _layers = filelayer.strip(path.read_bytes())
    obj = dbobject.parse(body)
    out = {}
    for bundle in obj.get("bundles") or []:
        for entry in bundle.get("ebx") or []:
            name = entry.get("name")
            sha1 = entry.get("sha1")
            if name and isinstance(sha1, bytes):
                out[name.lower()] = (sha1, int(entry.get("size") or 0))
    return out


overlay = entries(OVERLAY_SB)
vanilla = entries(VANILLA_SB)
print(f"overlay entries: {len(overlay)}   vanilla entries: {len(vanilla)}")

rows = [n for n in overlay if n.startswith("game/space/systems/systemdata/systemdata_")]
changed = [n for n in rows if n in vanilla and overlay[n][0] != vanilla[n][0]]
same = [n for n in rows if n in vanilla and overlay[n][0] == vanilla[n][0]]
missing = [n for n in rows if n not in vanilla]
print(f"systemdata entries in overlay: {len(rows)}")
print(f"  chunk sha1 CHANGED (our patch): {len(changed)}")
print(f"  chunk sha1 unchanged          : {len(same)}")
print(f"  not in vanilla                : {len(missing)}")
for name in sorted(changed)[:5]:
    print(f"    {name.rsplit('/', 1)[-1]:24s} vanilla {vanilla[name][0].hex()[:12]} "
          f"-> overlay {overlay[name][0].hex()[:12]}  size {overlay[name][1]}")
if same:
    for name in sorted(same)[:5]:
        print(f"    UNCHANGED {name.rsplit('/', 1)[-1]}")
