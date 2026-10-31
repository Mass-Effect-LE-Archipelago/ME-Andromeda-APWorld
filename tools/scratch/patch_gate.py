import sys, uuid
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite.partition import Partition

FALSE = uuid.UUID("c6660dbe-3614-11e5-aa63-b2e3b7222cc5")
TRUE = uuid.UUID("bf899768-3614-11e5-aa63-b2e3b7222cc5")

def orders(g):
    raw = g.bytes
    le = raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:]
    return {"be": raw, "le": le, "rev": raw[::-1]}

for name in ("destination_plt_kadaraunc", "destination_plt_eladen", "destination_plt_kearnosii"):
    path = Path("tools/scratch/dests") / (name + ".bin")
    if not path.exists():
        continue
    data = path.read_bytes()
    found = {label: data.count(pat) for label, pat in orders(FALSE).items()}
    print(f"{name} ({len(data)} bytes) counts {found}")
    if sum(found.values()):
        patched = data
        for label, pat in orders(FALSE).items():
            patched = patched.replace(pat, orders(TRUE)[label])
        out = Path("tools/scratch") / f"patched_{name}.bin"
        out.write_bytes(patched)
        part = Partition(patched)
        print(f"   patched -> {out.name}; parses with {len(list(part.instance_objects()))} objects, "
              f"same size {len(patched) == len(data)}")
