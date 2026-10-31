"""Confirm Frosty's overlay now carries v2 (38 rows + the prefab)."""
import datetime, hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))
from frostbite import dbobject, filelayer  # noqa: E402

GAME = Path(r"C:\Steam\steamapps\common\Mass Effect Andromeda")
OVERLAY = GAME / "ModData" / "Default" / "patch"
DIST = ROOT / "dist" / "galaxy-mods"


def entries(path: Path) -> dict[str, tuple[bytes, int]]:
    body, _ = filelayer.strip(path.read_bytes())
    obj = dbobject.parse(body)
    out = {}
    for bundle in obj.get("bundles") or []:
        for entry in bundle.get("ebx") or []:
            name, sha1 = entry.get("name"), entry.get("sha1")
            if name and isinstance(sha1, bytes):
                out[name.lower()] = (sha1, int(entry.get("size") or 0))
    return out


def compare(label: str, overlay_rel: str, vanilla_rel: str, prefixes: tuple[str, ...]) -> None:
    ov_path, va_path = OVERLAY / overlay_rel, GAME / vanilla_rel
    if not ov_path.is_file():
        print(f"{label}: overlay sb MISSING ({ov_path})")
        return
    overlay = entries(ov_path)
    vanilla = entries(va_path) if va_path.is_file() else {}
    names = [n for n in overlay if n.startswith(prefixes)]
    changed = [n for n in names if n in vanilla and overlay[n][0] != vanilla[n][0]]
    print(f"{label}: {len(names)} matching asset(s), {len(changed)} with a changed chunk sha1")
    for n in sorted(changed)[:3]:
        print(f"   {n.rsplit('/', 1)[-1]:24s} vanilla {vanilla[n][0].hex()[:12]} -> "
              f"overlay {overlay[n][0].hex()[:12]}")


compare("rows    ", "win32/galaxysystemcontent.sb", "Patch/Win32/galaxysystemcontent.sb",
        ("game/space/systems/systemdata/systemdata_",))
compare("prefab  ", "win32/game/levels/hubs/tempest/tempest.sb",
        "Patch/Win32/game/levels/hubs/tempest/tempest.sb",
        ("game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap",))

want = hashlib.sha256((DIST / "AP_GalaxyMap_v2_01.archive").read_bytes()).hexdigest()
print(f"\nlooking for v2 archive sha256 {want[:16]}â€¦ in the overlay")
hits = [p for p in OVERLAY.rglob("*") if p.is_file()
        and hashlib.sha256(p.read_bytes()).hexdigest() == want]
print(f"  found in {len(hits)} file(s): {[str(p.relative_to(OVERLAY)) for p in hits]}")
mods = OVERLAY / "mods.json"
print(f"\nmods.json: {mods.read_text(encoding='utf-8') if mods.is_file() else 'MISSING'}")
for rel in ("win32/galaxysystemcontent.sb", "win32/game/levels/hubs/tempest/tempest.sb"):
    p = OVERLAY / rel
    if p.is_file():
        stamp = datetime.datetime.fromtimestamp(p.stat().st_mtime)
        print(f"{rel}: {p.stat().st_size:,} B, written {stamp:%H:%M:%S}")

