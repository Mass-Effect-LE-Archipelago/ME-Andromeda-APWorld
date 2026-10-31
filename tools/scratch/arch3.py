from pathlib import Path
from compression import zstd

data = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
print("prefix:", data[:8].hex(" "), "| prefix u32be:", int.from_bytes(data[0:4], "big"),
      int.from_bytes(data[4:8], "big"))
d = zstd.ZstdDecompressor()
try:
    out = d.decompress(data[8:])
    print("decompress(data[8:]) ->", len(out), "bytes; head", out[:16].hex(" "))
except Exception as exc:
    print("failed:", type(exc).__name__, str(exc)[:80])
    # frame header carries its own content size; read it from the magic + descriptor
    print("frame header bytes:", data[8:8+8].hex(" "))
