"""How does spawnedgalaxymap actually spawn/enable a system? Dump the prefab's wiring."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import Partition  # noqa: E402

game = vfs.Game()
name = "game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap"
data, _ = game.chunk_data(game.resolve(name))
part = Partition(data)

bp = None
for inst, obj in part.instance_objects():
    if isinstance(obj, dict) and "PrefabBlueprint" in str(obj.get("$", "")):
        bp = obj
        break
print("PrefabBlueprint keys:", list(bp))

for key in ("Objects", "EventConnections", "LinkConnections", "PropertyConnections"):
    val = bp.get(key)
    print(f"\n=== {key}: {len(val) if isinstance(val, list) else type(val).__name__}")
    if isinstance(val, list):
        for i, item in enumerate(val[:3]):
            print(f"  [{i}] {str(item)[:400]}")
