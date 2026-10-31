import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
from frostbite.dbobject import ValueType
names = {v: k for k, v in vars(ValueType).items() if isinstance(v, int)}

def show(obj, indent="    "):
    for name, (tag, value) in obj:
        t = tag & 0x1F
        if t == ValueType.Object:
            print(f"{indent}{name} (object)")
            show(value, indent + "  ")
        elif t == ValueType.Bytes:
            print(f"{indent}{name} = {len(value)} bytes: {value[:40]!r}")
        elif t == ValueType.Array:
            print(f"{indent}{name} = [{len(value)}]")
            for item_tag, item in value:
                if (item_tag & 0x1F) == ValueType.Object:
                    show(item, indent + "  ")
                else:
                    print(f"{indent}  - {names.get(item_tag & 0x1F)} {str(item)[:40]}")
        else:
            print(f"{indent}{name} = {str(value)[:60]}")

for mod in ("Tempest Superstore Rank 01.fbmod", "ResearchableHalberd.fbmod"):
    data = (Path("Mass Effect Andromeda Mods") / mod).read_bytes()
    r = dbwrite.TypedReader(data, 0)
    _, root = r.value(r.u8() & 0x1F)
    d = {name: (tag, value) for name, (tag, value) in root}
    print(f"=== {mod}")
    print("  -- resources"); show(d["resources"][1])
    print("  -- actions"); show(d["actions"][1])
