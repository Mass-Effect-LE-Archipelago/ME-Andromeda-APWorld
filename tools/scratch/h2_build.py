"""H2: put Saajor's AvailableFlag (true) into a copy of Careerb191e387-0ManualSave.

The writer cannot grow the plot block, so one false bool that the game itself drops in the
next save (present-false here, absent in Chapter34) is replaced by the Saajor flag. Counts are
fixed width, so the block keeps its exact bit length.
"""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld\tools")
import profsave3 as p
import save_edit as se

SAVE_DIR = Path(r"C:\Users\unowi\Documents\BioWare\Mass Effect Andromeda\Save")
SRC = SAVE_DIR / "Careerb191e387-0ManualSave"
OUT = Path(sys.argv[1])
SAAJOR = "714a5805-c2f8-4552-a900-35da7f980121"

cur = p.load(SRC).plot["bools"]
nxt = p.load(SAVE_DIR / "Careerb191e387-Chapter34").plot["bools"]
prev = p.load(SAVE_DIR / "Careerb191e387-Chapter33").plot["bools"]
ch0 = p.load(SAVE_DIR / "Careerb191e387-Chapter0").plot["bools"]
cands = [k for k, v in cur.items() if v is True and nxt.get(k) is True and prev.get(k) is True and ch0.get(k) is True]
print("transient false candidates:", len(cands))
victim = cands[0]
print("dropping", victim)
assert SAAJOR not in cur


def mutate(plot):
    b = plot["bools"]
    del b[victim]
    b[SAAJOR] = False  # the reader's "false" list is the game's true list


def bit_splice(data_block, start_bit, end_bit, new_buf, new_bits):
    """Same as save_edit.splice, but for a region that does not start on a byte."""
    if new_bits != end_bit - start_bit:
        raise SystemExit("region length changed")
    out = bytearray(data_block)
    for i in range(new_bits):
        bit = (new_buf[i >> 3] >> (i & 7)) & 1
        j = start_bit + i
        if bit:
            out[j >> 3] |= 1 << (j & 7)
        else:
            out[j >> 3] &= ~(1 << (j & 7)) & 0xFF
    return out


se.splice = bit_splice
# Round-trip proof on this save: an untouched re-encode must reproduce the file exactly.
RT = OUT.with_name(OUT.name + ".roundtrip")
se.rewrite(SRC, RT, lambda plot: None)
assert RT.read_bytes() == SRC.read_bytes(), "round-trip differs"
print("round-trip identical")
RT.unlink()
se.rewrite(SRC, OUT, mutate)
after = p.load(OUT)
b = after.plot["bools"]
print("saajor ->", b.get(SAAJOR), "| victim present:", victim in b, "| bools", len(cur), "->", len(b))
diff = {k for k in set(cur) | set(b) if cur.get(k) != b.get(k)}
print("changed keys:", sorted(diff))
for kind in ("ints", "floats", "transforms"):
    assert after.plot[kind] == p.load(SRC).plot[kind], kind
print("ints/floats/transforms unchanged")



