import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
for label, path in (("alwaystrue", "tools/scratch/cond_true.bin"), ("alwaysfalse", "tools/scratch/cond_false.bin")):
    part = Partition(Path(path).read_bytes())
    print(f"{label}: partition guid {part.guid}")
    for name, obj in part.instance_objects():
        if isinstance(obj, dict):
            print("   fields:", ", ".join(list(obj.keys())[:10]))
            for key in ("$", "Name"):
                if key in obj:
                    print(f"   {key} = {obj[key]}")
