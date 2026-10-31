import sys
sys.path.insert(0, "tools")
sys.path.insert(0, "world/mass_effect_andromeda")
import client_core as cc
from pathlib import Path
S = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
WIN = {"SavedGame_HUB_Meridian"}
for name in ("Careerb191e387-Chapter34", "Careerb191e387-Chapter10", "Careerb191e387-5AutoSave", "Careerc8fa1bc8-Mission"):
    st = cc.CareerState.read(S / name)
    print(f"{name:34s} level={st.level:24s} win={st.level in WIN}")
