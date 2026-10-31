from pathlib import Path
names = [l.strip() for l in Path("data/asset-names.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
import re
patterns = {
    "galaxymap": re.compile(r"galaxymap|galaxy_map|galaxy/", re.I),
    "starmap":   re.compile(r"starmap|star_map", re.I),
    "worldmap":  re.compile(r"worldmap|world_map", re.I),
    "availability": re.compile(r"availability|unlock", re.I),
}
for label, pat in patterns.items():
    hits = [n for n in names if pat.search(n)]
    print(f"{label:14s} {len(hits):4d}")
    for n in hits[:8]:
        print(f"    {n[:100]}")
