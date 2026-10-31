"""Find the English text table and check whether it holds the system names."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import Partition  # noqa: E402

WANT = ["Pytheas", "Rohvir", "Remav", "Govorkam", "Fenodam", "Nexus", "Kadara", "Meridian"]

game = vfs.Game()
candidates = [
    "game/localization/config/texttable/en/game/levels/rootlevel/rootlevel",
    "game/localization/config/texttable/en/game/localization/config/globaltranslated",
    "game/localization/config/texttable/en/game/levels/mainmenu/mainmenu",
]
for name in candidates:
    records = game.find(name)
    if not records:
        print(f"{name}: not found")
        continue
    data = None
    for record in records:
        try:
            data, _loc = game.chunk_data(record)
            print(f"\n=== {name}  ({len(data)} bytes, {record.sb_path} / {record.bundle})")
            break
        except vfs.AssetError as exc:
            print(f"   listing {record.sb_path}: {exc}")
    if data is None:
        continue
    for marker in WANT:
        raw = marker.encode()
        print(f"   {marker:10s} {data.count(raw):3d} hit(s)")
    if data[:4] == b"\xce\xd1\xb2\x0f":
        part = Partition(data)
        print(f"   partition guid={part.guid.text} instances={len(part.instances)} "
              f"types={len(part.types)} imports={len(part.imports)}")
        types = {}
        for inst in part.instances:
            types[part.types[inst.type_index].label] = types.get(
                part.types[inst.type_index].label, 0) + 1
        print("   types:", types)
        for inst, obj in part.instance_objects():
            if not isinstance(obj, dict):
                continue
            keys = list(obj)[:8]
            print(f"   instance {inst.index} {part.types[inst.type_index].label} keys={keys}")
            for k in keys:
                print(f"      {k:24s} {str(obj[k])[:90]}")
            break
