"""Build data/regions.json from the asset name index.

Region identities come from the level codenames in the asset paths, and the codename ->
planet mapping is supported by the planet tokens that co-occur inside each area's assets
(e.g. 153 'elaaden' strings inside unc_dunes assets, 178 'voeld' inside unc_ice).

Run: python build_regions.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ROOT / "data" / "asset-names.txt"
OUT = ROOT / "data" / "regions.json"

# codename -> (display name, evidence)
MAP = [
    ("hub_nexus", "Nexus", "hub"),
    ("hub_aya", "Aya", "hub"),
    ("tempest", "Tempest", "hub"),
    ("hub_kadara", "Kadara (port)", "hub"),
    ("hub_meridian", "Meridian", "hub"),
    ("unc_stormcanyons", "Eos", "open world"),
    ("unc_ice", "Voeld", "open world"),
    ("unc_biolumin", "Havarl", "open world"),
    ("unc_outlaw", "Kadara", "open world"),
    ("unc_dunes", "Elaaden", "open world"),
    ("unc_lunar", "H-047c", "open world (space)"),
    ("crit_city", "Meridian (city)", "critical path"),
    ("crit_mer", "Meridian finale", "critical path"),
    ("crit_khet", "Kett flagship", "critical path"),
    ("crit_vlt", "Vault (critical)", "critical path"),
    ("crit_ex", "Exaltation facility", "critical path"),
    ("m0_prologue", "Hyperion prologue", "critical path"),
    ("m1_planetside", "Eos landing", "critical path"),
    ("m5_5_interlude", "Interlude", "critical path"),
    ("pro_lnd", "Planet landing", "critical path"),
]

PLANET_TOKENS = ["eos", "voeld", "havarl", "kadara", "elaaden", "meridian", "h-047", "lunar",
                 "nexus", "aya", "hyperion", "tempest"]


def main() -> int:
    names = [ln.strip() for ln in NAMES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    low = [n.lower() for n in names]
    regions = []
    for code, display, kind in MAP:
        hits = [n for n in low if code in n]
        tokens = Counter()
        for n in hits:
            for t in PLANET_TOKENS:
                if t in n:
                    tokens[t] += 1
        plot = sum(1 for n in hits if n.startswith("game/plots/"))
        journal = sum(1 for n in hits if n.startswith("game/journals/"))
        regions.append({
            "codename": code,
            "name": display,
            "kind": kind,
            "assets": len(hits),
            "plot_assets": plot,
            "journal_assets": journal,
            "planet_tokens": dict(tokens.most_common(4)),
        })
    data = {
        "source": "data/asset-names.txt",
        "note": "codename -> planet mapping is supported by the planet tokens that occur inside "
                "each area's asset paths; see docs/WORLD-MODEL.md",
        "regions": regions,
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(regions)} regions)")
    for r in regions:
        print(f"  {r['codename']:18s} {r['name']:16s} assets={r['assets']:6d} plot={r['plot_assets']:4d} "
              f"journal={r['journal_assets']:3d} tokens={r['planet_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
