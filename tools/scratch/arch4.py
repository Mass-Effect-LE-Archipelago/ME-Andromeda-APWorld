from pathlib import Path
from compression import zstd

data = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
magic = b"\x28\xb5\x2f\xfd"
offsets = []
i = data.find(magic)
while i >= 0:
    offsets.append(i)
    i = data.find(magic, i + 4)
print("zstd frames found:", len(offsets), "first few offsets:", offsets[:6])
d = zstd.ZstdDecompressor()
ok = 0
for idx, off in enumerate(offsets):
    end = offsets[idx + 1] if idx + 1 < len(offsets) else len(data)
    try:
        out = d.decompress(data[off:end])
        ebx = out[:4] == b"\xce\xd1\xb2\x0f"
        if idx < 4:
            print(f"  frame {idx} at {off:>8} span {end-off:>8} -> {len(out):>8} bytes ebx={ebx}")
        ok += 1
    except Exception as exc:
        if idx < 4:
            print(f"  frame {idx} at {off:>8} FAILED {type(exc).__name__}")
print(f"decompressed {ok} of {len(offsets)} spans")
