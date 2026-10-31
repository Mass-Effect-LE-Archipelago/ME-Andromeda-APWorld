"""Look for integer plot flags that behave like resources (research, credits, AVP, viability).

If such a flag exists and is writable, filler items could actually be delivered in game even
while weapons and planet access remain unsolved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"(research|credit|avp|viability|resource|points|xp|experience|pod|level|rank|count)", re.I)


def main() -> int:
    checks = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    ints = [c for c in checks if c["kind"] == "ints"]
    print(f"int checks: {len(ints)}")
    hits = [c for c in ints if PATTERN.search(c["label"])]
    print(f"resource-ish: {len(hits)}")
    for c in hits[:40]:
        value = str(c["value_in_reference_save"])[:10]
        print(f"  {value:10s}  {c['name'][:76]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
