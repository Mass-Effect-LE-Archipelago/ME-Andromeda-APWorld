import sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite

mods = sorted(Path("Mass Effect Andromeda Mods").glob("*.fbmod"))
ok = bad = skip = 0
for path in mods:
    data = path.read_bytes()
    try:
        r = dbwrite.TypedReader(data, 0)
        _, root_value = r.value(r.u8() & 0x1F)
        if r.pos != len(data):
            raise ValueError(f"trailing {len(data) - r.pos} bytes")
        rebuilt = dbwrite.write_root(1, root_value)   # tag is normalised below
        # the root tag byte must match the file's first byte
        same = rebuilt[1:] == data[1:] and len(rebuilt) == len(data)
        print(f"{'OK  ' if same else 'DIFF'} {path.name[:44]:44s} {len(data):9d} bytes")
        ok += same
        bad += (not same)
    except Exception as exc:
        skip += 1
        print(f"SKIP {path.name[:44]:44s} {type(exc).__name__}: {str(exc)[:40]}")
print(f"\nidentical {ok}, differing {bad}, skipped {skip} of {len(mods)}")
