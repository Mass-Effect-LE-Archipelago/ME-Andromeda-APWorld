import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p

SAVE = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave"
save = p.load(SAVE)
print("plot keys:", list(save.plot)[:10])
for kind in ("bools", "ints", "floats"):
    d = save.plot.get(kind, {})
    print(kind, len(d), "sample:", list(d.items())[:2])
    if kind == "bools":
        for probe in ("e49041e3-0643-406a-9c3f-b731506c01bf",
                      "E49041E3-0643-406A-9C3F-B731506C01BF"):
            print("  probe", probe, probe in d, d.get(probe))
        hits = [k for k in d if k.lower().startswith("e49041e3")]
        print("  startswith hits:", hits[:3], [d[k] for k in hits[:3]])
