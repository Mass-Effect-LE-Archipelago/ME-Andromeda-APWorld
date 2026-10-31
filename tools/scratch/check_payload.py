import json
from pathlib import Path
rel = Path(r"C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld\dist\release-mods")
inv = json.loads((rel / "mods.json").read_text(encoding="utf-8"))
files = {p.name for p in (rel / "mods").glob("*.fbmod")}
listed = {m["file"] for m in inv}
print("inventory entries:", len(listed), "| files present:", len(files))
print("listed but missing:", sorted(listed - files))
print("present but unlisted:", sorted(files - listed))
