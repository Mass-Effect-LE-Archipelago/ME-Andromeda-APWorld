import sys, collections
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

part = Partition(Path("tools/scratch/galaxymap.bin").read_bytes())
conds = []
for name, obj in part.instance_objects():
    if isinstance(obj, dict) and "PlotConditionNotificationEntityData" in str(obj.get("$", "")):
        conds.append(obj)
print(f"condition notification objects: {len(conds)}")
keys = collections.Counter()
for c in conds:
    for k in c:
        keys[k] += 1
print("fields present:", dict(keys))
for i, c in enumerate(conds[:6]):
    print(f"-- condition {i}")
    for k, v in c.items():
        print(f"   {k:30s} {str(v)[:70]}")
