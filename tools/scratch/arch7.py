import binascii, zlib
from pathlib import Path
from compression import zstd

d = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive").read_bytes()
for start in (0, 2605):
    hdr = d[start:start + 8]
    size = int.from_bytes(hdr[0:4], "big")
    be1 = int.from_bytes(hdr[4:8], "big")
    frame_at = d.find(b"\x28\xb5\x2f\xfd", start)
    fsize = zstd.get_frame_size(d[frame_at:])
    comp = d[frame_at:frame_at + fsize]
    out = zstd.decompress(comp)
    def fnv(b):
        h = 0x811C9DC5
        for byte in b:
            h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
        return h
    print(f"chunk@{start}: size={size} be1=0x{be1:08X} ({be1})")
    print(f"   crc32(comp)=0x{zlib.crc32(comp) & 0xFFFFFFFF:08X} crc32(raw)=0x{zlib.crc32(out) & 0xFFFFFFFF:08X}")
    print(f"   adler(raw)=0x{zlib.adler32(out) & 0xFFFFFFFF:08X} fnv(comp)=0x{fnv(comp):08X} fnv(raw)=0x{fnv(out):08X}")
    print(f"   len(comp)={len(comp)} len(raw)={len(out)} first_raw4={out[:4].hex()}")
