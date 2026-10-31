import sys, collections
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

def summarise(path):
    part = Partition(Path(path).read_bytes())
    objs = [o for _n, o in part.instance_objects() if isinstance(o, dict)]
    kinds = collections.Counter(str(o.get("$", "?")) for o in objs)
    names = [o.get("Name") for o in objs if isinstance(o.get("Name"), str)]
    return part, objs, kinds, names

for label, path in (("aya_01", "tools/scratch/sys_aya01.bin"), ("kadara_01", "tools/scratch/sys_kadara.bin")):
    part, objs, kinds, names = summarise(path)
    print(f"=== {label}  guid {part.guid}  objects {len(objs)}")
    for kind, n in kinds.most_common(8):
        print(f"    {n:4d}  {kind}")
    print(f"    named objects: {names[:4]}")
