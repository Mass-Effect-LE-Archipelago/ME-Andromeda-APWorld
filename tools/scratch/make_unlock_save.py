import json, sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
import profsave3 as p
import save_edit

part = Partition(Path("tools/scratch/galaxymap.bin").read_bytes())
flags = []
for _n, obj in part.instance_objects():
    if isinstance(obj, dict) and "PlotConditionNotificationEntityData" in str(obj.get("$", "")):
        for cond in obj.get("PlotConditions") or []:
            ref = (cond.get("PlotFlagReference") or {}).get("PlotFlagId") or {}
            if ref.get("Guid") is not None:
                flags.append(str(ref["Guid"]).lower())
flags = list(dict.fromkeys(flags))

src = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Careerc8fa1bc8-Mission"
save = p.load(src)
bools = save.plot.get("bools", {})
missing = [f for f in flags if f not in bools]
print(f"flags {len(flags)}, missing from the early save: {len(missing)}")

present = [f for f in flags if f in bools]
ops = [{"kind": "bool", "guid": f, "value": True} for f in present]
out = Path("tools/scratch/unlock-test.save")
log = save_edit.apply_batch(src, out, ops)
after = p.load(out)
ok = sum(1 for f in present if after.plot["bools"].get(f) is True)
print(f"applied {len(ops)} ops -> {ok} flags true in the output, {out.stat().st_size} bytes")
print(f"wrote {out}")
