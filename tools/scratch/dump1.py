import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbobject
path = Path("Mass Effect Andromeda Mods/Tempest Superstore Rank 01.fbmod")
data = path.read_bytes()
obj = dbobject.parse(data)
res = obj["resources"][0]
print("resource keys:", list(res.keys()))
print("shouldInline:", res.get("shouldInline"), " type:", res.get("type"), " name:", str(res.get("name"))[:40])
start, end = 0x440, 0x475
for off in range(start, end, 16):
    chunk = data[off:off+16]
    print(f"{off:04x}  {chunk.hex(' '):47s}  {''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)}")
