"""Do the readable UI bundles contain the galaxy-map system names as literal text?"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402

MARKERS = [b"Pytheas", b"Rohvir", b"Govorkam", b"Fenodam", b"Remav", b"Vaalon",
           b"Kindrax", b"Skeldah", b"Zaubray", b"Faroang", b"Eriksson", b"Zheng He"]
BUNDLES = ("sp_ui.sb", "ui.sb", "remcomp_labels.sb", "gamemusic.sb")

game = vfs.Game()
index = game.index()
names = [n for n, rows in index.items()
         if any(r.sb_path.endswith(b) for r in rows for b in BUNDLES)]
print(f"{len(names)} assets in {BUNDLES}")

hits = {}
for name in names:
    try:
        data, _ = game.chunk_data(game.resolve(name))
    except Exception:  # noqa: BLE001
        continue
    for m in MARKERS:
        if m in data:
            hits.setdefault(m.decode(), []).append(name)
print(f"markers found: {len(hits)}")
for marker, owners in hits.items():
    print(f"  {marker}: {len(owners)} asset(s), e.g. {owners[0]}")
