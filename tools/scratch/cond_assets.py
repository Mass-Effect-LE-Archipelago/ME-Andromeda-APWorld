import json
from pathlib import Path
hits = set()
for src in ("tools/scratch/join-sweep.json", "docs/plot-flag-join.json", "tools/scratch/join-sweep2.json"):
    path = Path(src)
    if not path.exists():
        continue
    for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
        for flag in asset.get("flags", []):
            if "ConditionLogicPrefabBlueprint" in flag.get("path", ""):
                hits.add(asset["name"])
sel = sorted(n for n in hits if "/space/" in n.lower() or "galaxy" in n.lower())
print(f"condition-logic assets: {len(hits)} total, {len(sel)} in space/galaxy")
for n in sel[:20]:
    print("  ", n[:100])
