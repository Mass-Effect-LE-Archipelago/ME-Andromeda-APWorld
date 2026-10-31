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
        raw_tag = r.u8()
        inner_tag, inner_value = r.value(raw_tag & 0x1F)
        if r.pos != len(data):
            raise ValueError(f"trailing {len(data) - r.pos} bytes")
        rebuilt = bytes([raw_tag]) + dbwrite.write_value(inner_tag, inner_value)
        same = rebuilt == data
        print(f"{'OK  ' if same else 'DIFF'} {path.name[:44]:44s} {len(data):9d}")
        ok += same; bad += (not same)
    except Exception as exc:
        skip += 1
        print(f"SKIP {path.name[:44]:44s} {type(exc).__name__}: {str(exc)[:38]}")
print(f"\nidentical {ok}, differing {bad}, skipped {skip} of {len(mods)}")
