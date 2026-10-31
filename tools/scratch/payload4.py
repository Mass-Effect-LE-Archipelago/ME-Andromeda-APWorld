from pathlib import Path
folder = Path("Mass Effect Andromeda Mods")
print("non-.fbmod files in the folder:", [p.name for p in folder.iterdir() if p.suffix.lower() != ".fbmod"][:10])
for name in ("Tempest Superstore Rank 01.fbmod", "ResearchableHalberd.fbmod", "MEA_Fixpack_1.05d.fbmod"):
    data = (folder / name).read_bytes()
    zstd = data.find(b"\x28\xb5\x2f\xfd")
    print(f"{name[:34]:34s} size {len(data):9d}  zstd magic at {zstd}  "
          f"first 16 {data[:16].hex(' ')}")
