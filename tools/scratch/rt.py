import sys
from pathlib import Path
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/frostbite")
from frostbite import dbwrite
from frostbite.dbobject import ValueType

mods = sorted(Path("Mass Effect Andromeda Mods").glob("*.fbmod"))
ok = bad = skipped = 0
for path in mods:
    data = path.read_bytes()
    # FBMODV2: DbObject starts after the 8-byte magic; find the root object tag heuristically
    # by trying offsets until a full parse consumes the rest.
    for start in (8, 9, 12, 16):
        try:
            r = dbwrite.TypedReader(data, start)
            tag = r.u8()
            value = r.value(tag & 0x1F)
            if r.pos != len(data):
                continue
            rebuilt = dbwrite.write_root(tag & 0x1F, value)
            same = rebuilt == data[start:]
            print(f"{'OK  ' if same else 'DIFF'} {path.name[:40]:40s} from +{start}")
            ok += same
            bad += (not same)
            break
        except Exception:
            continue
    else:
        skipped += 1
        print(f"SKIP {path.name[:40]:40s} (no clean DbObject root found)")
print(f"\nidentical {ok}, differing {bad}, skipped {skipped} of {len(mods)}")
