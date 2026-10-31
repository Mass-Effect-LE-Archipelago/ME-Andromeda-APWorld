import hashlib, sys
from pathlib import Path
for release in ("dist/release", "dist/release-mods"):
    root = Path(release)
    lines = (root / "SHA256SUMS.txt").read_text(encoding="utf-8").strip().splitlines()
    bad = 0
    for line in lines:
        digest, name = line.split("  ", 1)
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != digest:
            bad += 1
            print(f"  MISMATCH {name}")
    apworld = root / "mass_effect_andromeda.apworld"
    print(f"{release:20s} files {len(lines):3d}  bad {bad}  apworld {apworld.stat().st_size/1024:.0f} KB  "
          f"mods {len(list((root / 'mods').glob('*.fbmod'))) if (root / 'mods').exists() else 0}")
