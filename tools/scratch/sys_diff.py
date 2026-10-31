import sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition
def fields(path):
    part = Partition(Path(path).read_bytes())
    for name, obj in part.instance_objects():
        if isinstance(obj, dict):
            return obj
    return {}
a = fields("tools/scratch/sys_eos.bin"); b = fields("tools/scratch/sys_kadara.bin")
print(f"eos system fields {len(a)} | kadara system fields {len(b)}")
for key in sorted(set(a) | set(b)):
    sa, sb = str(a.get(key)), str(b.get(key))
    if sa != sb:
        print(f"  {key:30s} eos={sa[:34]:36s} kadara={sb[:34]}")
