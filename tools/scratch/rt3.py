import sys, traceback
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
data = Path("Mass Effect Andromeda Mods/Tempest Superstore Rank 01.fbmod").read_bytes()
r = dbwrite.TypedReader(data, 0)
tag = r.u8()
value = r.value(tag & 0x1F)
print("parsed ok, pos", hex(r.pos), "of", hex(len(data)))
try:
    dbwrite.write_root(tag & 0x1F, value)
except Exception:
    traceback.print_exc(limit=3)
