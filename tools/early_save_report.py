"""Full report on what the early save changes: named flips, per-system arrival gates, destinations.

Writes docs/EARLY-SAVE-FINDINGS.md so the evidence is durable.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
EARLY = SAVE_DIR / "Careerc8fa1bc8-Chapter0"
LATE = SAVE_DIR / "Career870ee94-1ManualSave"
OUT = ROOT / "docs" / "EARLY-SAVE-FINDINGS.md"
JOINS = ["docs/plot-flag-join.json", "tools/scratch/join-sweep.json",
         "tools/scratch/join-conv.json", "tools/scratch/join-sweep2.json"]

INTERESTING = re.compile(r"(arrivalgate|destination|unlock|galaxymap|planet|landing|system)", re.I)


def flags(save) -> dict[str, tuple[str, object]]:
    out = {}
    for kind in ("bools", "ints", "floats"):
        for guid, value in save.plot.get(kind, {}).items():
            out[guid] = (kind, value)
    return out


def main() -> int:
    early, late = p.load(EARLY), p.load(LATE)
    ef, lf = flags(early), flags(late)
    catalogue = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    named = {c["guid"]: c for c in catalogue}

    flipped = [g for g, (kind, v) in lf.items()
               if kind == "bools" and v is True and ef.get(g, ("bools", False))[1] is not True]

    # asset name -> guids referenced, from the joins
    asset_flags: dict[str, list[str]] = {}
    for src in JOINS:
        path = ROOT / src
        if not path.exists():
            continue
        for asset in json.loads(path.read_text(encoding="utf-8")).get("assets", []):
            for flag in asset.get("flags", []):
                asset_flags.setdefault(asset["name"], []).append(flag["guid"])

    lines: list[str] = []
    add = lines.append
    add("# Early-save findings (new career vs the 99.5% save)")
    add("")
    add(f"- early: `{EARLY.name}` — {early.data.get('timestamp_iso')} — **{len(ef)}** plot flags")
    add(f"- late : `{LATE.name}` — {late.data.get('timestamp_iso')} — **{len(lf)}** plot flags")
    add(f"- flags false in early and true in late: **{len(flipped)}**")
    add(f"- of those named by the catalogue: **{len([g for g in flipped if g in named])}**")
    add("")

    named_flips = [named[g] for g in flipped if g in named]
    counts = Counter(c["region"] for c in named_flips)
    add("## Named flips by region")
    add("")
    for region, n in counts.most_common():
        add(f"- {region}: {n}")
    add("")

    add("## Named flips (all)")
    add("")
    for entry in sorted(named_flips, key=lambda c: (c["region"], c["name"])):
        add(f"- `{entry['kind']}` **{entry['name']}** — `{entry['best_source'][-70:]}`")
    add("")

    # arrival gates: every flag referenced by an asset whose path mentions arrivalgate/destination
    add("## Arrival gates and destinations")
    add("")
    interesting = {name: guids for name, guids in asset_flags.items()
                   if INTERESTING.search(name) and ("/space/" in name or "/plots/" in name)}
    for name in sorted(interesting):
        guids = interesting[name]
        rows = []
        for guid in guids:
            if guid.startswith("00000000-"):
                continue
            early_v = ef.get(guid, ("absent", None))[1]
            late_v = lf.get(guid, ("absent", None))[1]
            if early_v != late_v:
                rows.append((guid, early_v, late_v))
        if not rows:
            continue
        add(f"### {name}")
        add("")
        for guid, early_v, late_v in rows[:12]:
            label = named.get(guid, {}).get("name")
            add(f"- `{guid}` {early_v!r} -> {late_v!r}" + (f"  ({label})" if label else "  (unnamed)"))
        add("")

    # what is already true in a fresh career, per region
    add("## What a fresh career already has (named flags true in the early save)")
    add("")
    early_true = [named[g] for g in ef if g in named and ef[g][1] is True]
    add(f"total named true: **{len(early_true)}**")
    for region, n in Counter(c["region"] for c in early_true).most_common():
        add(f"- {region}: {n}")
    add("")
    for entry in sorted(early_true, key=lambda c: (c["region"], c["name"]))[:80]:
        add(f"- `{entry['kind']}` **{entry['name']}**")
    add("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(lines)} lines)")
    print(f"early flags {len(ef)}, flips {len(flipped)}, named flips {len(named_flips)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
