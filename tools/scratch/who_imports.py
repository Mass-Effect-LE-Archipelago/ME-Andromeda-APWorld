"""Which assets under a prefix import a given partition GUID (e.g. a plot expression)?
Usage: python who_imports.py <partition guid> <prefix> [prefix...]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import probe_galaxymap_prefab as probe  # noqa: E402
from frostbite import vfs  # noqa: E402

target = sys.argv[1].lower()
game = vfs.Game()
n = 0
for prefix in sys.argv[2:]:
    for name in game.iter_names(prefix):
        if not name.startswith(prefix):
            continue
        _d, part = probe.partition_or_none(game, name)
        n += 1
        if part is None or not hasattr(part, "imports"):
            continue
        if any(pg.text.lower() == target for pg, _ig in part.imports):
            print(name)
print(f"scanned {n}")

