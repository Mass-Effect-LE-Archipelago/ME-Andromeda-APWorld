from pathlib import Path
folder = Path("Mass Effect Andromeda Mods")
for path in sorted(folder.glob("*.archive")):
    d = path.read_bytes()
    print(f"{path.name[:42]:42s} {len(d):9d}  {d[:12].hex(' ')}")
