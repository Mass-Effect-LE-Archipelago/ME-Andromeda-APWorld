"""Find the flag(s) that are false in every pre-finale save and true in every post-finale save."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
# strictly before the Meridian finale
BEFORE = [f"Careerb191e387-{n}" for n in
          ("Chapter0", "Chapter1", "Chapter51", "Chapter30", "Chapter4", "Chapter31", "Chapter6",
           "Chapter53", "Chapter33", "0ManualSave", "Chapter34")]
# after it
AFTER = ["Careerb191e387-Chapter10", "Careerb191e387-Mission"] + \
        [f"Careerb191e387-{n}AutoSave" for n in ("6", "7", "8", "9", "0", "1", "2", "3", "4", "5")]
WITNESS_SAVES = ["Careerc8fa1bc8-Chapter0", "Careerc8fa1bc8-Mission", "Career870ee94-1ManualSave"]


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    before = []
    for name in BEFORE:
        path = SAVE_DIR / name
        if path.exists():
            before.append((name, flags(p.load(path))))
    after = []
    for name in AFTER:
        path = SAVE_DIR / name
        if path.exists():
            after.append((name, flags(p.load(path))))
    print(f"before saves {len(before)}, after saves {len(after)}")

    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c["name"] for c in catalogue}

    candidates = []
    for guid, (kind, value) in after[0][1].items():
        if kind != "bools" or value is not True:
            continue
        if any(f.get(guid, ("bools", False))[1] is True for _, f in before):
            continue
        if not all(f.get(guid, ("bools", False))[1] is True for _, f in after):
            continue
        candidates.append(guid)

    print(f"candidates false-in-all-before / true-in-all-after: {len(candidates)}")
    for guid in candidates[:40]:
        label = named.get(guid, "")
        print(f"  {guid}  {label}")

    # witnesses: is the candidate true in the other careers' saves too?
    print("\nwitness saves (early career should be false, finished true):")
    for name in WITNESS_SAVES:
        path = SAVE_DIR / name
        if not path.exists():
            continue
        f = flags(p.load(path))
        true_count = sum(1 for g in candidates if f.get(g, ("bools", False))[1] is True)
        print(f"  {name:32s} {true_count}/{len(candidates)} true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
