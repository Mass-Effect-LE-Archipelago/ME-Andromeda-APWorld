import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"

FLAGS = {
    "aya_01": "e49041e3-0643-406a-9c3f-b731506c01bf",
    "aya_06": "7625031e-726d-4a44-916b-78fcd6c1019f",
    "kadara_01": "d3cce618-0b27-4a64-ae60-505b6f760168",
    "kadara_02": "874d381f-7da3-4d8b-95b5-939afcd601c6",
    "nexus_01": "7a584ac3-29f7-47c4-b725-b39bf6c5010a",
    "meridian_01": "714a5805-c2f8-4552-a900-35da7f980121",
}

saves = sorted(SAVE_DIR.iterdir(), key=lambda q: q.name)
print(f"{len(saves)} saves in {SAVE_DIR}")
for path in saves:
    if not path.is_file():
        continue
    try:
        save = p.load(path)
    except Exception as exc:  # noqa: BLE001
        print(f"  {path.name:34s} <unreadable: {exc}>")
        continue
    bools = save.plot.get("bools", {})
    ints = save.plot.get("ints", {})
    cells = []
    for label, guid in FLAGS.items():
        if guid in bools:
            cells.append(f"{label}=B:{int(bools[guid])}")
        elif guid in ints:
            cells.append(f"{label}=I:{ints[guid]}")
        else:
            cells.append(f"{label}=absent")
    print(f"  {path.name:34s} bools={len(bools):6d}  " + " ".join(cells))

dump = ROOT / "docs" / "Career870ee94.plot.json"
doc = json.loads(dump.read_text(encoding="utf-8"))
print("\nplot json keys:", list(doc)[:8])
for kind, values in doc.items():
    if isinstance(values, dict):
        print(f"  {kind}: {len(values)} entries; sample {list(values.items())[:2]}")
