import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
from frostbite.dbobject import Guid
import profsave3 as p

part = Partition(Path("tools/scratch/galaxymap.bin").read_bytes())
flags = []
for name, obj in part.instance_objects():
    if isinstance(obj, dict) and "PlotConditionNotificationEntityData" in str(obj.get("$", "")):
        for cond in obj.get("PlotConditions") or []:
            ref = (cond.get("PlotFlagReference") or {}).get("PlotFlagId") or {}
            if ref.get("Guid") is not None:
                flags.append(str(ref["Guid"]).lower())
flags = list(dict.fromkeys(flags))
print(f"map flags: {len(flags)}")

S = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
for label, name in (("fresh M0", "Careerc8fa1bc8-Chapter0"), ("M1", "Careerc8fa1bc8-Mission"),
                    ("ladder M1", "Careerb191e387-Chapter1"), ("87%", "Careered8233e3-0ManualSave"),
                    ("99.5%", "Career870ee94-1ManualSave")):
    path = S / name
    if not path.exists():
        continue
    save = p.load(path)
    bools = save.plot.get("bools", {})
    true_count = sum(1 for f in flags if bools.get(f) is True)
    present = sum(1 for f in flags if f in bools)
    print(f"{label:10s} true {true_count:2d}/{len(flags)}  present {present:2d}")
