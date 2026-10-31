import re, sys, uuid
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite import vfs

guids = ["a668f233-aa39-9b8a-9e54-bc3fbbf9bffe", "e207ddf3-4b19-033b-d782-dbdc0d73dbbf",
         "e137ca53-b212-1738-94c7-74eafa5e7213", "a83fbd59-cb68-0930-3eee-c7a54e7f9632",
         "bc4b8e86-768d-26c0-a49a-efc1a1ca8781", "17d09122-8095-8a38-b324-2b3e70148488"]
def pats(g):
    raw = uuid.UUID(g).bytes
    return [raw, raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:], raw[::-1]]
groups = {g: pats(g) for g in guids}

names = [l.strip() for l in Path("data/asset-names.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
sel = [n for n in names if re.search(r"galaxymap|galaxy|starmap", n, re.I) and "/audio/" not in n]
print("candidates:", len(sel))
game = vfs.Game()
scored = []
checked = 0
for name in sel:
    try:
        data, _ = game.chunk_data(game.resolve(name))
    except Exception:
        continue
    checked += 1
    hits = [g for g, group in groups.items() if any(p in data for p in group)]
    if hits:
        scored.append((len(hits), name))
scored.sort(reverse=True)
print(f"checked {checked}; with jump references: {len(scored)}")
for count, name in scored[:15]:
    print(f"  {count:3d}  {name[:90]}")
