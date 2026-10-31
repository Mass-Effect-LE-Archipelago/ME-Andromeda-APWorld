import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbobject

for mod in ("Tempest Superstore Rank 01.fbmod", "ResearchableHalberd.fbmod"):
    obj = dbobject.parse((Path("Mass Effect Andromeda Mods") / mod).read_bytes())
    print(f"=== {mod}")
    for i, res in enumerate(obj["resources"][:3]):
        print(f"  resource[{i}]:")
        for key, value in res.items():
            if isinstance(value, (bytes, bytearray)):
                print(f"    {key:16s} bytes[{len(value)}] {value[:32]!r}")
            else:
                print(f"    {key:16s} {str(value)[:56]}")
    for i, act in enumerate(obj["actions"][:3]):
        print(f"  action[{i}]: { {k: (str(v)[:40]) for k, v in act.items()} }")
