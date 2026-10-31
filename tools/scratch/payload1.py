import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
from frostbite.dbobject import ValueType

names = {v: k for k, v in vars(ValueType).items() if isinstance(v, int)}
for mod in ("Tempest Superstore Rank 01.fbmod", "ResearchableHalberd.fbmod"):
    data = (Path("Mass Effect Andromeda Mods") / mod).read_bytes()
    r = dbwrite.TypedReader(data, 0)
    tag = r.u8()
    _, root = r.value(tag & 0x1F)
    print(f"=== {mod} ({len(data)} bytes)")
    for name, (child_tag, value) in root:
        t = child_tag & 0x1F
        size = len(value) if isinstance(value, (bytes, list)) else value
        print(f"  {name:14s} {names.get(t, t):8s} {str(size)[:60]}")
    res = dict(root)["resources"][1]
    print("  resources:", len(res), "entries")
    for entry_name, (etag, entry) in list(res)[0][1][1]:
        print(f"    {entry_name:16s} {names.get(etag & 0x1F, etag):9s} {str(entry)[:50]}")
