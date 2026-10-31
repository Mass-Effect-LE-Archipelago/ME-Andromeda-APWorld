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
        disp = obj.get("DisplayCondition") or {}
        hide = obj.get("HideCondition") or {}
        jump = obj.get("JumpToSystem") or {}
        interesting = {k: v for k, v in {**disp, **hide}.items() if v not in (None, 0) and not str(k).startswith("$")}
        print(f"  locator State={obj.get('State')} Visible={obj.get('Visible')} "
              f"jump={str(jump.get('__import__'))[:8]}  conditions={interesting}")
