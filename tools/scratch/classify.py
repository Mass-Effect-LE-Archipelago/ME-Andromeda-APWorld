import sys
from pathlib import Path
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/frostbite")
from frostbite import dbobject

mods = sorted(Path("Mass Effect Andromeda Mods").glob("*.fbmod"))
v2, other = [], []
for path in mods:
    data = path.read_bytes()
    try:
        obj = dbobject.parse(data)
        v2.append(path.name)
        print(f"V2   {path.name[:46]:46s} keys={len(obj)}")
    except Exception as exc:
        other.append(path.name)
        print(f"v1?  {path.name[:46]:46s} {type(exc).__name__}: {str(exc)[:50]}")
print(f"\nDbObject-parsable: {len(v2)}   other: {len(other)}")
