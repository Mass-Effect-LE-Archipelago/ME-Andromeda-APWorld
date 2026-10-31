from pathlib import Path
p = Path("tools/build_planet_mod.py")
s = p.read_text(encoding="utf-8").replace('put(action, "resourceId", "0")', 'put(action, "resourceId", 0)')
p.write_text(s, encoding="utf-8")
print("patched resourceId to int")
