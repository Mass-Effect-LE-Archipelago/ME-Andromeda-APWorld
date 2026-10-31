import collections, sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
part = Partition(Path("tools/scratch/galaxymap.bin").read_bytes())
objs = [o for _n, o in part.instance_objects() if isinstance(o, dict)]
print(f"guid {part.guid}  objects {len(objs)}")
print("types:")
for kind, n in collections.Counter(str(o.get("$", "?")) for o in objs).most_common(10):
    print(f"  {n:4d}  {kind}")
conn = [o for o in objs if "PrefabBlueprint" in str(o.get("$", ""))]
for bp in conn:
    for key in ("PropertyConnections", "LinkConnections", "EventConnections", "Objects"):
        val = bp.get(key)
        if isinstance(val, list):
            print(f"  {key}: {len(val)} entries")
