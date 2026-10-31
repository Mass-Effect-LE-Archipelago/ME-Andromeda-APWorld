import sys
sys.path.insert(0, "tools")
sys.path.insert(0, "world/mass_effect_andromeda")
import client_core as cc
from pathlib import Path
S = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
wins = []
for path in sorted((f for f in S.iterdir() if f.is_file() and f.name.startswith("Career")),
                   key=lambda f: f.stat().st_mtime):
    st = cc.CareerState.read(path)
    if st.level == "SavedGame_HUB_Meridian":
        wins.append(path.name)
print("saves satisfying the goal:", wins)
