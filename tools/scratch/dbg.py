import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
from frostbite.dbobject import ValueType

path = Path("Mass Effect Andromeda Mods/Tempest Superstore Rank 01.fbmod")
data = path.read_bytes()
r = dbwrite.TypedReader(data, 0)
tag = r.u8()
names = []

orig_array = dbwrite.TypedReader.array
def traced_array(self):
    start = self.pos
    declared = self.packed()
    end = self.pos + declared
    items = []
    while True:
        t = self.u8()
        if (t & 0x1F) == 0:
            break
        items.append(self.value(t & 0x1F))
    if self.pos != end:
        print(f"array at 0x{start:X} declared_end=0x{end:X} actual=0x{self.pos:X} diff={self.pos-end}")
        print(f"  context: {'/'.join(names[-6:])}")
        print(f"  bytes near end: {data[end-8:end+8].hex(' ')}")
        raise SystemExit(1)
    return items
dbwrite.TypedReader.array = traced_array

orig_object = dbwrite.TypedReader.object
def traced_object(self):
    start = self.pos
    end = self.pos + self.packed()
    out = []
    while True:
        t = self.u8()
        if (t & 0x1F) == 0:
            break
        name = self.cstring()
        names.append(f"{name}[0x{self.pos:X}]")
        out.append((name, self.value(t & 0x1F)))
    if self.pos != end:
        print(f"object at 0x{start:X} declared_end=0x{end:X} actual=0x{self.pos:X} diff={self.pos-end}")
        print(f"  context: {'/'.join(names[-6:])}")
        raise SystemExit(1)
    return out
dbwrite.TypedReader.object = traced_object

r.value(tag & 0x1F)
print("parsed to", hex(r.pos), "of", hex(len(data)))
