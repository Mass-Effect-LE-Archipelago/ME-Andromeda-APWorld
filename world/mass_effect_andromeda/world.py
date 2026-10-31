from __future__ import annotations

import logging
from typing import Any, ClassVar

from worlds.AutoWorld import WebWorld, World

from . import data, items, options as mea_options, regions, rules

logger = logging.getLogger(__name__)


class MassEffectAndromedaWebWorld(WebWorld):
    game_info_languages = ["en"]
    theme = "dirt"


class MassEffectAndromedaWorld(World):
    """
    Mass Effect Andromeda. The Tempest, the Nexus and one destination are open at the start;
    every other planet, story mission, squadmate and weapon is scattered across the multiworld.
    Plot flags observed in the save are the checks; the campaign is won by completing Meridian.
    """

    game = data.GAME_NAME
    web = MassEffectAndromedaWebWorld()
    options_dataclass = mea_options.MassEffectAndromedaOptions
    options: mea_options.MassEffectAndromedaOptions
    origin_region_name = "Tempest"

    item_name_to_id: ClassVar[dict[str, int]] = data.ITEM_NAME_TO_ID
    location_name_to_id: ClassVar[dict[str, int]] = data.LOCATION_NAME_TO_ID
    item_name_groups = data.ITEM_NAME_GROUPS
    location_name_groups = data.LOCATION_NAME_GROUPS

    included_locations: list[data.LocationData]

    def generate_early(self) -> None:
        self.included_locations = [
            loc for loc in data.LOCATIONS
            if not (self.options.bool_checks_only and loc.kind != "bools")
        ]
        regions_with_checks = {loc.region for loc in self.included_locations}
        # A ship region with no checks left in it is not worth a region node, but keep the
        # travel regions so access items always open something.
        self.included_regions = set(data.TRAVEL_REGIONS) | (
            set(data.SHIP_REGIONS) & regions_with_checks)
        logger.info("%s: %d locations across %d regions", self.player_name,
                    len(self.included_locations), len(self.included_regions))

    def create_regions(self) -> None:
        regions.create_regions(self)

    def create_item(self, name: str) -> items.MassEffectAndromedaItem:
        return items.create_item(self, name)

    def create_items(self) -> None:
        items.create_items(self)

    def get_filler_item_name(self) -> str:
        return self.random.choice(data.FILLER_ITEMS)

    def set_rules(self) -> None:
        rules.set_rules(self)

    def fill_slot_data(self) -> dict[str, Any]:
        detectors = []
        for loc in self.included_locations:
            detectors.append({
                "id": data.LOCATION_NAME_TO_ID[loc.name],
                "name": loc.name,
                "region": loc.region,
                "guid": loc.guid,
                "kind": loc.kind,
            })
        return {
            "slot_data_version": data.SCHEMA_VERSION,
            "schema": 1,
            "starting_region": self.options.starting_region.current_key,
            "weapon_items": bool(self.options.weapon_items),
            "bool_checks_only": bool(self.options.bool_checks_only),
            # No single plot flag separates pre- and post-finale (verified: 0 candidates across
            # 11 before / 12 after saves), so the win is the save's location tag. The Meridian hub
            # only exists once the finale is complete, which makes it unambiguous; the client
            # latches the win, so leaving the hub afterwards cannot un-win the seed.
            "goal": {"kind": "level", "levels": ["SavedGame_HUB_Meridian"],
                     "mission_item": "Priority Op: Meridian"},
            "access": {k: v for k, v in data.ACCESS_ITEMS.items()},
            "missions": {k: v for k, v in data.MISSION_ACCESS.items()},
            "detectors": detectors,
        }
