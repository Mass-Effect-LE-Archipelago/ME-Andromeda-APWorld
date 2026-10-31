import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
part = Partition(Path("tools/scratch/sys_kadara.bin").read_bytes())
print("guid", part.guid)
for name, obj in part.instance_objects():
    if isinstance(obj, dict):
        print(f"object with {len(obj)} fields:")
        for key, value in obj.items():
            print(f"   {key:32s} {str(value)[:64]}")
