import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite import vfs
game = vfs.Game()
for name in ("game/space/destinations/plt/destination_plt_kadaraunc",
             "game/space/destinations/plt/destination_plt_kearnosii"):
    rec = game.resolve(name)
    print(f"{name.rsplit('/',1)[-1]:28s} superbundle={rec.superbundle}  size={rec.size}")
