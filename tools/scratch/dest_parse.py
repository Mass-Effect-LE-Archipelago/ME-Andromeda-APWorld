import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

raw = Path("tools/scratch/dest_eos.json").read_bytes()
part = Partition(raw)
print("guid:", part.guid)
objs = list(part.instance_objects())
print(f"objects: {len(objs)}")
for name, obj in objs:
    if not isinstance(obj, dict):
        continue
    print(f"object {name}: {len(obj)} fields")
    for key, value in obj.items():
        print(f"   {key:32s} {str(value)[:66]}")
