import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
import fbmod
rec = fbmod.parse(Path("Mass Effect Andromeda Mods/betterDeconstruction.fbmod"))
print("resources:", len(rec["assets"]), "| format", rec["format"])
dests = [a for a in rec["assets"] if "destinations" in a.lower() or "/space/" in a.lower()]
print("space-related resources:", len(dests))
for d in dests[:10]:
    print("  ", d)
print("sample resources:", rec["assets"][:3])
