from pathlib import Path
from compression import zstd
data = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
print("prefix", data[:8].hex(" "))
off = 8
frames = ebx = 0
total_out = 0
while off < len(data):
    try:
        size = zstd.get_frame_size(data[off:])
        out = zstd.decompress(data[off:off + size])
    except Exception as exc:
        print(f"  stop at {off}: {type(exc).__name__} {str(exc)[:40]}")
        break
    if frames < 3:
        print(f"  frame {frames} at {off:>8} compressed {size:>7} -> {len(out):>7} bytes ebx={out[:4] == b'\xce\xd1\xb2\x0f'}")
    frames += 1
    total_out += len(out)
    ebx += out[:4] == b"\xce\xd1\xb2\x0f"
    off += size
print(f"frames {frames}, ebx partitions {ebx}, uncompressed total {total_out}, ended at {off} of {len(data)}")
