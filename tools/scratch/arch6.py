from pathlib import Path
from compression import zstd
d = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
for start in (0, 2605):
    hdr = d[start:start + 8]
    nxt = d.find(b"\x28\xb5\x2f\xfd", start)
    size = zstd.get_frame_size(d[nxt:]) if nxt >= 0 else 0
    print(f"header at {start:>8}: {hdr.hex(' ')}  be0={int.from_bytes(hdr[0:4],'big')} be1={int.from_bytes(hdr[4:8],'big')} frame {nxt} size {size}")
