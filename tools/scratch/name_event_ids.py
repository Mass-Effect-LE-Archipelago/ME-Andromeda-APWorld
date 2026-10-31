"""Name the prefab's event/field ids: is `djb` the hash, and what do the event ids mean?"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import Partition, djb  # noqa: E402

game = vfs.Game()
data, _ = game.chunk_data(game.resolve(
    "game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap"))
part = Partition(data)

# 1. sanity: does djb reproduce a known field-name hash?
known = {f.name_hash: f.label for f in part.fields if f.name}
sample = next(f for f in part.fields if f.label == "CheckOnStart")
print(f"djb('CheckOnStart') = {djb('CheckOnStart'):#010x}   header hash = {sample.name_hash:#010x}   "
      f"match={djb('CheckOnStart') == sample.name_hash}")
print(f"djb('PlotConditions') = {djb('PlotConditions'):#010x}   "
      f"header hash = {next(f.name_hash for f in part.fields if f.label == 'PlotConditions'):#010x}")

# 2. collect ids used in connections
ids = {"SourceEvent": set(), "TargetEvent": set(),
       "SourceFieldId": set(), "TargetFieldId": set()}
bp = next(obj for _i, obj in part.instance_objects()
          if isinstance(obj, dict) and "PrefabBlueprint" in str(obj.get("$", "")))
for names in ("EventConnections", "PropertyConnections", "LinkConnections"):
    for conn in bp.get(names) or []:
        for key in ids:
            value = conn.get(key)
            if isinstance(value, dict):
                value = value.get("Id")
            if isinstance(value, int):
                ids[key].add(value & 0xFFFFFFFF)
print({k: len(v) for k, v in ids.items()})

CANDIDATES = [
    "OnTrue", "OnFalse", "True", "False", "OnStart", "OnStop", "Start", "Stop",
    "Spawn", "Despawn", "Show", "Hide", "Enable", "Disable", "Activate", "Deactivate",
    "Visible", "Hidden", "Reveal", "Conceal", "Open", "Close", "Begin", "End",
    "OnSpawn", "OnDespawn", "OnShow", "OnHide", "OnEnable", "OnDisable",
    "ConditionTrue", "ConditionFalse", "ConditionMet", "ConditionUnmet",
    "PlotConditionTrue", "PlotConditionFalse", "OnConditionTrue", "OnConditionFalse",
    "StartEvent", "StopEvent", "SpawnEvent", "DespawnEvent",
    "VisibleChanged", "Visibility", "SetVisible", "SetHidden",
    "Play", "StopPlay", "OnPlay", "OnFinish", "Finished", "Complete", "Completed",
    "Enter", "Exit", "OnEnter", "OnExit", "State", "SetState", "Change", "Changed",
]
wanted = ids["SourceEvent"] | ids["TargetEvent"] | ids["SourceFieldId"] | ids["TargetFieldId"]
found = {}
for cand in CANDIDATES:
    h = djb(cand)
    if h in wanted:
        found[h] = cand
print(f"names recovered: {len(found)} of {len(wanted)} ids")
for h, cand in found.items():
    print(f"  {h:#010x} -> {cand}")
