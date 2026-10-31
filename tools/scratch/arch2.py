from pathlib import Path
data = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
from compression import zstd
print("module:", [n for n in dir(zstd) if "Decomp" in n or n == "decompress"])
try:
    out = zstd.decompress(data[8:])
    print("decompress all:", len(out), out[:16].hex(" "))
except Exception as exc:
    print("all failed:", type(exc).__name__, exc)
    dctx = zstd.ZstdDecompressor() if hasattr(zstd, "ZstdDecompressor") else None
    if dctx:
        obj = dctx.decompressobj()
        out = obj.decompress(data[8:])
        print("stream:", len(out), "unused", len(obj.unused_data) if hasattr(obj, "unused_data") else "?")
