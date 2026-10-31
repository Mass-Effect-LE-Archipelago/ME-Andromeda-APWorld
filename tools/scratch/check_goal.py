import sys
sys.path.insert(0, "tools")
sys.path.insert(0, "world/mass_effect_andromeda")
import client_core as cc
from pathlib import Path

LEVELS = {"SavedGame_HUB_Meridian", "SavedGame_UNC_Eos"}
MIN_KEYS = 40
S = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
rows = []
for path in sorted((f for f in S.iterdir() if f.is_file() and f.name.startswith("Career")),
                   key=lambda f: f.stat().st_mtime):
    st = cc.CareerState.read(path)
    win = st.level in LEVELS and len(set(st.world_map)) >= MIN_KEYS
    rows.append((path.name, st.level, len(set(st.world_map)), win))
for name, level, keys, win in rows:
    print(f"{name:34s} {level:24s} keys {keys:3d}  win={win}")
print("wins marked:", sum(1 for r in rows if r[3]))
