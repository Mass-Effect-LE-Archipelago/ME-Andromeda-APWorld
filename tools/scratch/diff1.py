import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite

for name in ("Tempest Superstore Rank 01.fbmod", "ResearchableHalberd.fbmod"):
    data = (Path("Mass Effect Andromeda Mods") / name).read_bytes()
    r = dbwrite.TypedReader(data, 0)
    raw_tag = r.u8()
    inner_tag, inner_value = r.value(raw_tag & 0x1F)
    rebuilt = bytes([raw_tag]) + dbwrite.write_value(inner_tag, inner_value)
    print(f"=== {name}  orig {len(data)}  rebuilt {len(rebuilt)}")
    if rebuilt == data:
        print("  identical")
        continue
    limit = min(len(data), len(rebuilt))
    first = next(i for i in range(limit) if data[i] != rebuilt[i])
    print(f"  first diff at 0x{first:X}")
    lo = max(0, first - 24); hi = min(limit, first + 24)
    print(f"  orig : {data[lo:hi].hex(' ')}")
    print(f"  new  : {rebuilt[lo:hi].hex(' ')}")
    print(f"  orig ascii: {''.join(chr(b) if 32 <= b < 127 else '.' for b in data[lo:hi])}")
