"""Anchor the bool-list orientation on squad-recruited flags (known story timing)."""
import json, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld\tools")
import profsave3 as p

J = json.loads(Path(r"C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld\docs\plot-flag-join.json").read_text(encoding="utf-8"))
D = Path(r"C:\Users\unowi\Documents\BioWare\Mass Effect Andromeda\Save")
chain = ["Chapter0", "Chapter1", "Chapter51", "Chapter30", "Chapter4", "Chapter31", "Chapter6",
         "Chapter53", "Chapter33", "0ManualSave", "Chapter34", "Chapter10"]
saves = {c: p.load(D / f"Careerb191e387-{c}").plot["bools"] for c in chain}
sym = {True: "T", False: "f", None: "."}
print(" " * 60 + " ".join(c[-4:] for c in chain))
for a in J["assets"]:
    if "global/squad/" in a["name"] and a["name"].endswith("_recruited") or "galaxymap_unlock_meridian" in a["name"]:
        for f in a["flags"]:
            g = f["guid"]
            row = "    ".join(sym[saves[c].get(g)] for c in chain)
            print(f"{a['name'].split('/')[-1][:30]:30s} {g[:8]} {f['path'][:18]:18s}  {row}")
