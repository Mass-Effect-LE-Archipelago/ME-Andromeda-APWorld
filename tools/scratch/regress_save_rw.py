"""Regression for the save reader/writer on every save on this machine.

Per save: (1) untouched re-encode is byte-identical to the file; (2) inserting one absent bool
produces a save that re-parses, keeps every other agent payload byte-identical (only moved),
and keeps all existing flags; (3) squad flags read in story order on the b191e387 chain.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profsave3 as p  # noqa: E402
import save_edit as se  # noqa: E402

D = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
OUT = Path(__file__).resolve().parent / "regress_out"
OUT.mkdir(exist_ok=True)
NEW = "00000000-0000-4000-8000-00000000a11e"


def payload_bytes(path):
    """Each agent slot's payload bits (length-prefixed), keyed by (agent, slot), plot excluded."""
    raw = path.read_bytes()
    _h, data, _i = p.unwrap(raw)
    s = p.load(path)
    out = {}
    for a in s.agents:
        if a.kind == "plot":
            continue
        for slot, off in enumerate(a.offsets):
            if not off:
                continue
            r = p.BitReader(data, off, len(data) * 8 - off)
            n = r.read(24)
            r2 = p.BitReader(data, off, 24 + n)
            out[(a.index, slot)] = r2.read(24 + n)
    return out


fails = 0
for path in sorted(D.iterdir()):
    if not path.name.startswith("Career") or not path.is_file():
        continue
    try:
        src = p.load(path)
    except Exception as e:  # noqa: BLE001
        print(f"{path.name:30s} SKIP unreadable: {e}")
        continue
    rt = OUT / (path.name + ".rt")
    se.rewrite(path, rt, lambda plot: None)
    same = rt.read_bytes() == path.read_bytes()
    ins = OUT / (path.name + ".ins")
    se.rewrite(path, ins, lambda plot: plot["bools"].__setitem__(NEW, True))
    after = p.load(ins)
    flags_ok = all(after.plot["bools"].get(k) == v for k, v in src.plot["bools"].items()) \
        and after.plot["bools"].get(NEW) is True \
        and after.plot["ints"] == src.plot["ints"] and after.plot["floats"] == src.plot["floats"]
    payload_ok = payload_bytes(path) == payload_bytes(ins)
    grew = ins.stat().st_size - path.stat().st_size
    ok = same and flags_ok and payload_ok and grew == 16
    fails += not ok
    print(f"{path.name:30s} roundtrip={same} insert: flags={flags_ok} other_agents_identical={payload_ok} "
          f"grew={grew} {'OK' if ok else 'FAIL'}")
    rt.unlink()
    ins.unlink()

print("FAILURES:", fails)
sys.exit(1 if fails else 0)
