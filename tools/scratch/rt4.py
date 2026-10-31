import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
data = Path("Mass Effect Andromeda Mods/Tempest Superstore Rank 01.fbmod").read_bytes()
r = dbwrite.TypedReader(data, 0)
tag = r.u8()
value = r.value(tag & 0x1F)
print("root tag", tag, "type", type(value))
for name, inner in value[:3]:
    print(" field", name, "->", type(inner), repr(inner)[:60])
    if isinstance(inner, tuple):
        print("   inner tag", inner[0], "value type", type(inner[1]), repr(inner[1])[:60])
        if isinstance(inner[1], list) and inner[1]:
            print("   first element:", repr(inner[1][0])[:80])
