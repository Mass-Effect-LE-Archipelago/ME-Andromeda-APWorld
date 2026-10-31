import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))
import fbmod  # noqa: E402
from frostbite import modarchive  # noqa: E402

MODS = ROOT / "Mass Effect Andromeda Mods"

for mod_name, arc_name in [
    ("betterDeconstruction.fbmod", "betterDeconstruction_01.archive"),
    ("ResearchableHalberd.fbmod", "ResearchableHalberd_01.archive"),
]:
    mod_path, arc_path = MODS / mod_name, MODS / arc_name
    if not mod_path.is_file():
        print(f"{mod_name}: missing")
        continue
    parsed = fbmod.parse(mod_path)
    res = parsed["resources"]
    chunks = modarchive.parse(arc_path.read_bytes())
    print(f"\n=== {mod_name}: {len(res)} resources, {len(chunks)} chunks")
    print(f"archive bytes {arc_path.stat().st_size:,}  sum(comp) {sum(len(c.compressed) for c in chunks):,}"
          f"  sum(comp+8) {sum(len(c.compressed) + 8 for c in chunks):,}")
    print(f"offsets ascending? {all(res[i]['offset'] <= res[i+1]['offset'] for i in range(len(res)-1))}")
    print(f"archiveIndex values: {sorted({r.get('archive_index') for r in res})}")
    print("first 6 resources:")
    for r in res[:6]:
        print(f"   idx={r['archive_index']} off={r['offset']:8d} comp={r['compressed_size']:6d} "
              f"uncomp={r['uncompressed_size']:6d} {r['name'][-45:]}")
    print("first 6 chunks:")
    for c in chunks[:6]:
        print(f"   hdr_off={c.offset:8d} comp={len(c.compressed):6d} uncomp={len(c.data):6d}")
    offs = {r["offset"] for r in res}
    print(f"resource offsets == chunk header offsets? {len(offs & {c.offset for c in chunks})} match")
    print(f"resource offsets == chunk data offsets (hdr+8)? "
          f"{len(offs & {c.offset + 8 for c in chunks})} match")
    print(f"max resource offset {max(offs):,}")
