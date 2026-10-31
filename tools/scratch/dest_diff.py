import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

def fields(path):
    part = Partition(Path(path).read_bytes())
    for name, obj in part.instance_objects():
        if isinstance(obj, dict):
            return obj, part.guid
    return {}, None

eos, eos_guid = fields("tools/scratch/dest_eos.json")
kad, kad_guid = fields("tools/scratch/dest_kadara.bin")
print(f"eos guid {eos_guid} fields {len(eos)} | kadara guid {kad_guid} fields {len(kad)}")
for key in sorted(set(eos) | set(kad)):
    a, b = eos.get(key), kad.get(key)
    sa, sb = str(a), str(b)
    if sa != sb and not key.startswith("Autopilot"):
        print(f"  {key:32s} eos={sa[:40]:42s} kadara={sb[:40]}")
