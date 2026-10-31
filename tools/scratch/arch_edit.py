import re, sys
from pathlib import Path
sys.path.insert(0, "tools")
from frostbite import modarchive

src = Path("Mass Effect Andromeda Mods/betterDeconstruction_01.archive")
raw = src.read_bytes()
chunks = modarchive.parse(raw)
print(f"parsed {len(chunks)} chunks, chunk0 {len(chunks[0].data)} bytes magic {chunks[0].data[:4].hex()}")
strings = [m.group(0) for m in re.finditer(rb"[ -~]{12,}", chunks[0].data)]
target = next((s for s in strings if b"/" in s), strings[0])
print(f"target string: {target[:60]!r}")
mutated = bytearray(chunks[0].data)
pos = mutated.find(target) + target.find(b"/") + 1
old = mutated[pos]
mutated[pos] = ord("Z") if old != ord("Z") else ord("Y")
modarchive.replace(chunks[0], bytes(mutated))
print(f"mutated byte {pos}: {chr(old)!r} -> {chr(mutated[pos])!r}")
out = modarchive.rebuild(chunks)
reparsed = modarchive.parse(out)
ok = bytes(reparsed[0].data) == bytes(mutated) and all(len(c.data) == c.size for c in reparsed)
print(f"rebuilt {len(out)} bytes (was {len(raw)}), chunks {len(reparsed)}, consistent {ok}")
dest = Path("tools/scratch/edited-betterDeconstruction_01.archive")
dest.write_bytes(out)
print(f"wrote {dest} ({dest.stat().st_size} bytes)")
