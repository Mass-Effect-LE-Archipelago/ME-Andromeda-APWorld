import json, sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
from frostbite.dbobject import Guid

part = Partition(Path("tools/scratch/galaxymap.bin").read_bytes())
save_flags = set()
plot = Path("docs/Career870ee94.plot.json")
if plot.exists():
    data = json.loads(plot.read_text(encoding="utf-8"))
    for kind in ("bools", "ints", "floats"):
        save_flags.update(data.get(kind, {}))

rows = []
for name, obj in part.instance_objects():
    if not isinstance(obj, dict) or "PlotConditionNotificationEntityData" not in str(obj.get("$", "")):
        continue
    for cond in obj.get("PlotConditions") or []:
        ref = (cond.get("PlotFlagReference") or {}).get("PlotFlagId") or {}
        guid = ref.get("Guid")
        if guid is None:
            continue
        text = str(guid).lower()
        rows.append((text, cond.get("DesiredValue"), text in save_flags))
print(f"conditions: {len(rows)}")
for text, desired, in_save in rows[:40]:
    print(f"  {text}  desired={desired}  in_finished_save={in_save}")
print(f"in finished save: {sum(1 for r in rows if r[2])} of {len(rows)}")
