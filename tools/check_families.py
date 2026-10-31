"""Report which asset families the named checks come from, to tune the quality filter."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
checks = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]

family = Counter()
for c in checks:
    best = c.get("best_source", c["sources"][0]).lower()
    parts = best.split("/")
    family["/".join(parts[:2]) if len(parts) > 1 else best] += 1

print(f"checks: {len(checks)}")
for k, v in family.most_common(20):
    print(f"  {v:5d}  {k}")

print("\nsample of the noisiest labels:")
labels = Counter(c["label"] for c in checks)
for label, n in labels.most_common(15):
    print(f"  {n:4d}  {label}")
