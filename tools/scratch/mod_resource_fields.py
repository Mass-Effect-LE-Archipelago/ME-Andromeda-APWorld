import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))
import fbmod_write  # noqa: E402
from frostbite import vfs  # noqa: E402

MOD = ROOT / "Mass Effect Andromeda Mods" / "betterDeconstruction.fbmod"
rt, it, inner = fbmod_write.load(MOD)
print("root fields:", [k for k, _v in inner])
res_tag, res_value = dict((k, v) for k, v in inner)["resources"]
print("resources array length:", len(res_value))
first = res_value[0][1]
print("first resource fields:")
for k, (tag, value) in first:
    shown = value.hex() if isinstance(value, bytes) else value
    print(f"  {k:16s} tag={tag} value={shown}")

game = vfs.Game()
rec = game.resolve("game/items/research/projects/gear/arms/researchproject_gear_arms_angaraguerilla")
print("\ngame record:")
print(f"  sha1={rec.sha1.hex()} size={rec.size} original_size={rec.original_size}")
print(f"  bundle={rec.bundle}")

data, _loc = game.chunk_data(rec)
import hashlib
print(f"  sha1 of decompressed data: {hashlib.sha1(data).hexdigest()}")
print(f"  sha1 of compressed chunk:  {hashlib.sha1(_loc and b'' or b'').hexdigest()}")
