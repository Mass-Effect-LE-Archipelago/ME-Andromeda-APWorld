import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

for label, path in (("aya_01", "tools/scratch/sys_aya01.bin"), ("kadara_01", "tools/scratch/sys_kadara.bin")):
    part = Partition(Path(path).read_bytes())
    print(f"=== {label}")
    for _name, obj in part.instance_objects():
        if not isinstance(obj, dict) or "SystemDestinationLocator" not in str(obj.get("$", "")):
            continue
        print("  locator:")
        for key, value in obj.items():
            print(f"    {key:28s} {str(value)[:70]}")
