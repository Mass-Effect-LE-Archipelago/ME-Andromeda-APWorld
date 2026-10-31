"""Static data for the Mass Effect Andromeda world.

The check catalogue and item pool are generated from the game files by
`tools/build_checks.py` and `tools/build_items.py` and shipped in `datafiles/`.
Location and item IDs are assigned deterministically from sorted names, so a given
catalogue always produces the same IDs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

GAME_NAME = "Mass Effect Andromeda"

# Regions the player can travel to, in the order they appear in the game's own level data.
TRAVEL_REGIONS: tuple[str, ...] = (
    "Tempest", "Nexus", "Hyperion", "Aya", "Eos", "Voeld", "Havarl",
    "Kadara", "Elaaden", "H-047c", "Meridian",
)

# Regions that are not a destination but a bag of checks reachable from the Tempest.
SHIP_REGIONS: tuple[str, ...] = (
    "Squad: Jaal", "Squad: Peebee", "Squad: Cora", "Squad: Vetra", "Squad: Liam", "Squad: Drack",
    "Crew: techofficer", "Crew: doctor", "Crew: pilot", "Crew: scienceofficer",
    "Outposts", "Colonial Life", "Trust", "Main Plot", "Pathfinder",
    "Loyalty Missions", "Space", "Vault", "Exaltation Facility", "Kett Flagship", "Global",
)

# Access items. Key = item name, value = the region it opens.
PLANET_ACCESS: dict[str, str] = {
    "Eos Access": "Eos",
    "Voeld Access": "Voeld",
    "Havarl Access": "Havarl",
    "Kadara Access": "Kadara",
    "Elaaden Access": "Elaaden",
    "H-047c Access": "H-047c",
    "Meridian Access": "Meridian",
}
HUB_ACCESS: dict[str, str] = {
    "Nexus Access": "Nexus",
    "Aya Access": "Aya",
}
# Story gates. The game's priority-op ladder (game/journals/0_priorityops).
MISSION_ACCESS: dict[str, str] = {
    "Priority Op: A Better Beginning": "m1_planetside",
    "Priority Op: The First Vault": "m2_firstvault",
    "Priority Op: Exaltation": "m3_exaltation",
    "Priority Op: Kett Flagship": "m4_kettflagship",
    "Priority Op: Remnant City": "m5_remnantcity",
    "Priority Op: Meridian": "m7_meridian",
}

FILLER_ITEMS: tuple[str, ...] = (
    "Research Data", "Credits", "Vanadium", "Element Zero", "Ammo Pack", "Med Kit",
)

VICTORY_EVENT = "Meridian Victory"


@dataclass(frozen=True)
class LocationData:
    name: str
    region: str
    guid: str
    kind: str
    value: object
    source: str


def _load(name: str) -> dict:
    # importlib.resources reads from a zipimport-ed .apworld as well as a plain folder.
    # `__package__` is empty when this module is imported standalone (ad-hoc tooling), so fall
    # back to the package name and then to a filesystem read.
    package = __package__ or "mass_effect_andromeda"
    try:
        return json.loads(resources.files(package).joinpath(f"datafiles/{name}").read_text(encoding="utf-8"))
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        return json.loads((Path(__file__).resolve().parent / "datafiles" / name).read_text(encoding="utf-8"))


def _unique(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    i = 2
    while f"{name} ({i})" in used:
        i += 1
    final = f"{name} ({i})"
    used.add(final)
    return final


def _build_locations() -> list[LocationData]:
    raw = _load("checks.json")["checks"]
    used: set[str] = set()
    out: list[LocationData] = []
    for entry in raw:
        region = entry["region"]
        if region not in TRAVEL_REGIONS and region not in SHIP_REGIONS:
            region = "Other"
        name = _unique(entry["name"], used)
        out.append(LocationData(name=name, region=region, guid=entry["guid"],
                                kind=entry["kind"], value=entry["value_in_reference_save"],
                                source=entry["sources"][0] if entry["sources"] else ""))
    out.sort(key=lambda loc: (loc.region, loc.name))
    return out


def _build_weapons() -> list[str]:
    raw = _load("items.json")["weapons"]
    return [f"{w['name'].title()} {w['class']}" for w in raw]


LOCATIONS: list[LocationData] = _build_locations()
LOCATION_BY_NAME: dict[str, LocationData] = {loc.name: loc for loc in LOCATIONS}

WEAPONS: list[str] = _build_weapons()

ACCESS_ITEMS: dict[str, str] = {**PLANET_ACCESS, **HUB_ACCESS}

ITEM_NAMES: list[str] = sorted(set(ACCESS_ITEMS) | set(MISSION_ACCESS) | set(WEAPONS) | set(FILLER_ITEMS))

LOCATION_NAME_TO_ID: dict[str, int] = {loc.name: i + 1 for i, loc in enumerate(sorted(LOCATIONS, key=lambda l: l.name))}
ITEM_NAME_TO_ID: dict[str, int] = {name: i + 1 for i, name in enumerate(ITEM_NAMES)}

LOCATION_NAME_GROUPS: dict[str, set[str]] = {}
for _loc in LOCATIONS:
    LOCATION_NAME_GROUPS.setdefault(_loc.region, set()).add(_loc.name)

ITEM_NAME_GROUPS: dict[str, set[str]] = {
    "Access": set(ACCESS_ITEMS),
    "Missions": set(MISSION_ACCESS),
    "Weapons": set(WEAPONS),
    "Filler": set(FILLER_ITEMS),
}

SCHEMA_VERSION = 1
