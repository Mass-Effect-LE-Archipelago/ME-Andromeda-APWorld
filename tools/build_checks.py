"""Build data/checks.json: the named check catalogue.

Inputs:
  docs/plot-flag-join.json      asset name -> plot flag GUIDs (produced by tools/frostbite)
  docs/Career870ee94.plot.json  the 99.5% save, for current values
  data/regions.json             codename -> region display names

Output: one entry per save flag that has at least one named source asset, with a readable
label, the region it belongs to, its kind, and its value in the reference save.

Run: python build_checks.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOINS = [ROOT / "docs" / "plot-flag-join.json", ROOT / "tools" / "scratch" / "join-sweep.json",
         ROOT / "tools" / "scratch" / "join-conv.json", ROOT / "tools" / "scratch" / "join-sweep2.json"]
SAVE = ROOT / "docs" / "Career870ee94.plot.json"
OUT = ROOT / "data" / "checks.json"

# Ordered token rules: the first token found anywhere in the asset path wins.
REGION_TOKENS = [
    ("conversations/hubs/hub_nexus", "Nexus"),
    ("conversations/hubs/hub_aya", "Aya"),
    ("conversations/hubs/hub_kad", "Kadara"),
    ("conversations/hubs/hub_tem", "Tempest"),
    ("conversations/unc/olw", "Kadara"),
    ("conversations/unc/storms", "Eos"),
    ("conversations/unc/biolum", "Havarl"),
    ("conversations/unc/ice", "Voeld"),
    ("conversations/unc/des", "Elaaden"),
    ("conversations/unc/lunar", "H-047c"),
    ("conversations/crit/crit_mer", "Meridian"),
    ("conversations/crit/crit_ex", "Exaltation Facility"),
    ("conversations/crit/m4", "Kett Flagship"),
    ("conversations/loyalty", "Loyalty Missions"),
    ("conversations/banter", "Tempest"),
    ("conversations/storyteller", "Global"),
    ("plots/squadmates/jaal", "Squad: Jaal"),
    ("plots/squadmates/peebee", "Squad: Peebee"),
    ("plots/squadmates/cora", "Squad: Cora"),
    ("plots/squadmates/vetra", "Squad: Vetra"),
    ("plots/squadmates/liam", "Squad: Liam"),
    ("plots/squadmates/drack", "Squad: Drack"),
    ("plots/crew/techofficer", "Crew: techofficer"),
    ("plots/crew/doctor", "Crew: doctor"),
    ("plots/crew/pilot", "Crew: pilot"),
    ("plots/crew/scienceofficer", "Crew: scienceofficer"),
    ("plots/systems/outposts", "Outposts"),
    ("plots/bstory/coloniallife", "Colonial Life"),
    ("plots/global/trust", "Trust"),
    ("plots/global/missions", "Main Plot"),
    ("plots/global/pathfinder", "Pathfinder"),
    ("hub_nexus", "Nexus"),
    ("hub_aya", "Aya"),
    ("hub_tempest", "Tempest"),
    ("hub_kadara", "Kadara"),
    ("hub_meridian", "Meridian"),
    ("crit_city", "Meridian"),
    ("crit_mer", "Meridian"),
    ("m5_5_interlude", "Meridian"),
    ("m5_remnantcity", "Meridian"),
    ("m7_meridian", "Meridian"),
    ("unc_storm", "Eos"),
    ("unc_ice", "Voeld"),
    ("unc_biolumin", "Havarl"),
    ("unc_outlaw", "Kadara"),
    ("unc_dunes", "Elaaden"),
    ("unc_lunar", "H-047c"),
    ("m1_planetside", "Eos"),
    ("m0_prologue", "Hyperion"),
    ("crit_khet", "Kett Flagship"),
    ("crit_ex", "Exaltation Facility"),
    ("crit_vlt", "Vault"),
    ("loyalty", "Loyalty Missions"),
    ("journals/0_priorityops", "Main Plot"),
    ("journals/hubs/hub_nexus", "Nexus"),
    ("journals/hubs/hub_aya", "Aya"),
    ("journals/hubs/tempest", "Tempest"),
    ("journals/unc/ice", "Voeld"),
    ("journals/unc/des", "Elaaden"),
    ("journals/unc", "Eos"),
    ("journals/2_heleus", "Global"),
    ("space/", "Space"),
    ("storyteller", "Global"),
    ("prefabs/logic", "Global"),
    ("rootlevel", "Global"),
]


def region_for(name: str) -> str:
    low = name.lower()
    for token, region in REGION_TOKENS:
        if token in low:
            return region
    return "Global"


def label_for(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def nice(text: str) -> str:
    text = text.replace("_plotlogic_", " / ").replace("plotlogic/", "")
    parts = re.split(r"[_/]", text)
    words = [p for p in parts if p]
    out = []
    for w in words:
        if w.lower() in ("check",):
            out.append("check")
        elif w.isdigit():
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:] if w.islower() else w)
    return " ".join(out)


JUNK = re.compile(
    r"(debug|zzdebug|mainflow|galaxycompletion|squadselectionux|streaming|spawner|levelsetup|"
    r"quickstart|henchstate|worldevent_clear|objectivemarkers|test|tutorial|placeholder|dummy|"
    r"design|schematic|_sch$|_sc$|startpoints|markers?$)",
    re.I)
STRONG = re.compile(
    r"(check|available|journal|found|allglyphs|ready|recruited|complete|objective|unlock|"
    r"eligible|done|active|tracked)", re.I)
CLEAN_FAMILY = re.compile(r"^game/(plots|journals|space|storyteller|conversations)/", re.I)


def quality(name: str) -> int:
    """Higher is better.

    Only the game's own plot, journal, space and storyteller assets are used. The huge
    `game/levels/**` tail is real plot state but its flags are level scaffolding
    (`zzdebug`, `mainflow`, `objectives`, streaming triggers), which makes terrible checks;
    it is excluded until it can be filtered by meaning rather than by name.
    """
    if not CLEAN_FAMILY.match(name):
        return -5
    leaf = name.rsplit("/", 1)[-1]
    if JUNK.search(leaf):
        return -5
    score = 3
    if STRONG.search(leaf):
        score += 2
    if "/plots/" in name.lower():
        score += 1
    return score


def main() -> int:
    save = json.loads(SAVE.read_text(encoding="utf-8"))
    assets: list[dict] = []
    for join_path in JOINS:
        if not join_path.exists():
            print(f"skip missing join: {join_path}")
            continue
        join = json.loads(join_path.read_text(encoding="utf-8"))
        print(f"{join_path.name}: {len(join['assets'])} assets, stats={join.get('stats')}")
        assets.extend(join["assets"])

    # guid -> (kind, value) from the reference save
    values: dict[str, tuple[str, object]] = {}
    for kind in ("bools", "ints", "floats"):
        for g, v in save.get(kind, {}).items():
            values[g] = (kind, v)

    # Collect every candidate source per flag, then keep the best one.
    candidates: dict[str, list[tuple[int, str, str]]] = {}
    for asset in assets:
        name = asset["name"]
        q = quality(name)
        for flag in asset.get("flags", []):
            g = flag["guid"]
            if g not in values:
                continue
            candidates.setdefault(g, []).append((q, name, flag.get("path", "")))

    by_guid: dict[str, dict] = {}
    dropped = 0
    dropped_float = 0
    for g, cands in candidates.items():
        cands.sort(key=lambda c: (-c[0], c[1]))
        best_q, best_name, best_path = cands[0]
        if best_q < 0:
            dropped += 1
            continue
        kind, value = values[g]
        if kind == "floats":
            # The client cannot detect float flags: there is no stable "done" semantics for a
            # float and a location nobody can check would sit unfinished forever.
            dropped_float += 1
            continue
        region = region_for(best_name)
        label = label_for(best_name)
        by_guid[g] = {
            "guid": g,
            "kind": kind,
            "value_in_reference_save": value,
            "region": region,
            "label": label,
            "name": f"{region}: {nice(label)}",
            "quality": best_q,
            "best_source": best_name,
            "sources": sorted({c[1] for c in cands}),
            "flag_paths": sorted({c[2] for c in cands if c[2]}),
        }

    checks = sorted(by_guid.values(), key=lambda c: (c["region"], c["label"], c["guid"]))
    by_region = Counter(c["region"] for c in checks)
    by_kind = Counter(c["kind"] for c in checks)
    data = {
        "source_join": "docs/plot-flag-join.json",
        "source_save": "docs/Career870ee94.plot.json",
        "note": "one entry per save flag reachable from a named plot asset; "
                "'name' is derived from the asset leaf, not from a localization table",
        "stats": {
            "named_checks": len(checks),
            "flags_in_save": len(values),
            "coverage_percent": round(100.0 * len(checks) / max(1, len(values)), 2),
            "by_region": dict(by_region.most_common()),
            "by_kind": dict(by_kind),
        },
        "checks": checks,
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"  named checks: {len(checks)} of {len(values)} save flags "
          f"({data['stats']['coverage_percent']}%)")
    print(f"  dropped: {dropped} low quality, {dropped_float} float-only")
    print(f"  by kind: {dict(by_kind)}")
    print("  by region:")
    for r, n in by_region.most_common():
        print(f"    {n:5d}  {r}")
    print("  sample names:")
    for c in checks[:8]:
        print(f"    {c['kind']:6s} {c['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
