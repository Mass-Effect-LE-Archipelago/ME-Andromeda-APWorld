import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402

game = vfs.Game()
index = game.index()
print(f"index names: {len(index)}")
by_sb = {}
for name, rows in index.items():
    for r in rows:
        key = r.sb_path.rsplit("/", 1)[-1] if "/" in r.sb_path else r.sb_path
        by_sb.setdefault(r.sb_path, 0)
        by_sb[r.sb_path] += 1
print("superbundles in the index:")
for path, n in sorted(by_sb.items()):
    print(f"  {n:7d}  {path}")

loc = [n for n, rows in index.items()
       if any("loctext" in r.sb_path.lower() or "\\loc\\" in r.sb_path.lower() for r in rows)]
print(f"\nnames listed in loc/loctext superbundles: {len(loc)}")
for n in loc[:15]:
    print("  ", n)
