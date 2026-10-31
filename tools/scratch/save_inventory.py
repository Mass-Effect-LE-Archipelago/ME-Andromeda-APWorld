"""Where is every save? Header location tag, level, save name, timestamp, flag count."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"

rows = []
for path in sorted(SAVE_DIR.iterdir(), key=lambda q: q.name):
    if not path.is_file() or not path.name.startswith("Career"):
        continue
    try:
        s = p.load(path)
    except Exception as exc:  # noqa: BLE001
        rows.append((path.name, f"<unreadable: {exc}>", "", "", "", 0))
        continue
    d = s.data
    bools = len(s.plot.get("bools", {}))
    entry1 = s.header.get("entry1", "")
    rows.append((path.name, entry1, d.get("save_file_name", ""),
                 d.get("level_name", ""), d.get("timestamp_iso", ""), bools))

print(f"{'file':34s} {'entry1':24s} {'bools':6s} {'level':34s} {'timestamp'}")
for name, entry1, save_name, level, ts, bools in rows:
    print(f"{name:34s} {entry1:24s} {bools:<6d} {level:34s} {ts}")
print(f"\n{len(rows)} save(s)")
