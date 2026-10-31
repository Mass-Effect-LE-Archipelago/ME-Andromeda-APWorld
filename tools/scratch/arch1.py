import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import compress

data = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
print("size", len(data), "prefix", data[:8].hex(" "))
offset = 8
for i in range(4):
    out, consumed = compress.decompress(data, offset)
    print(f"  frame {i} at {offset}: consumed {consumed}, decompressed {len(out)}, head {out[:12].hex(' ')}")
    offset += consumed
print("after 4 frames:", offset, "of", len(data))
