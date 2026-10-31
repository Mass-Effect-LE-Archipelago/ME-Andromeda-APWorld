"""Can the 38 conditions be patched? Locate CheckOnStart and the flag GUID per condition."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import DT_BOOLEAN, Partition  # noqa: E402

game = vfs.Game()
name = "game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap"
data, _ = game.chunk_data(game.resolve(name))
part = Partition(data)
print(f"{name}: {len(data)} bytes, {len(part.instances)} instances")

rows = []
for inst, obj in part.instance_objects():
    if not isinstance(obj, dict) or "PlotConditionNotificationEntityData" not in str(obj.get("$", "")):
        continue
    type_def = part.types[inst.type_index]
    # the fields live on the base type named in "$"
    base_index = None
    for fi in range(type_def.field_start, type_def.field_start + type_def.field_count):
        f = part.fields[fi]
        if f.label == "$":
            base_index = f.type_index
    fields = {}
    for type_index in [i for i in (base_index, inst.type_index) if i is not None]:
        td = part.types[type_index]
        for fi in range(td.field_start, td.field_start + td.field_count):
            f = part.fields[fi]
            fields.setdefault(f.label, (f.data_type, inst.data_offset + f.data_offset))
    check = fields.get("CheckOnStart")
    trigger = fields.get("TriggerOnValueChange")
    rows.append((inst.index, check, trigger,
                 part.data[check[1]] if check and check[0] == DT_BOOLEAN else None,
                 part.data[trigger[1]] if trigger and trigger[0] == DT_BOOLEAN else None,
                 inst.guid is not None))

print(f"condition instances: {len(rows)}")
for idx, check, trigger, check_val, trig_val, named in rows[:5]:
    print(f"  inst {idx:3d} checkOnStart@{check[1]:#x}={check_val} "
          f"trigger@{trigger[1]:#x}={trig_val} named={named}")
print("checkOnStart values:", {r[3] for r in rows})
print("triggerOnValueChange values:", {r[4] for r in rows})
print("all instances carry an instance GUID:", all(r[5] for r in rows))
