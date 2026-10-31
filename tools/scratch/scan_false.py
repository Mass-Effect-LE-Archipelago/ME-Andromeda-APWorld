import sys, uuid
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite import vfs
from frostbite.partition import Partition

def guid_of(path):
    return Partition(Path(path).read_bytes()).guid

true_guid = guid_of("tools/scratch/cond_true.bin")
false_guid = guid_of("tools/scratch/cond_false.bin")
print("alwaystrue  ", true_guid)
print("alwaysfalse ", false_guid)

def patterns(g):
    raw = uuid.UUID(str(g)).bytes
    return {raw, raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:], raw[::-1]}

false_pats = patterns(false_guid)
game = vfs.Game()
names = [n for n in game.iter_names("game/space/") if n.startswith("game/space/")]
print("scanning", len(names), "space assets")
hits = []
for name in names:
    try:
        data, _ = game.chunk_data(game.resolve(name))
    except Exception:
        continue
    if any(p in data for p in false_pats):
        hits.append(name)
print(f"assets referencing alwaysfalse: {len(hits)}")
for name in hits[:20]:
    print("  ", name)
