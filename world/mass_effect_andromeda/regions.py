from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import ItemClassification, Location, LocationProgressType, Region

from . import data
from .items import MassEffectAndromedaItem

if TYPE_CHECKING:
    from .world import MassEffectAndromedaWorld


class MassEffectAndromedaLocation(Location):
    game = data.GAME_NAME


def _requires(state, player: int, *items: str) -> bool:
    return all(state.has(item, player) for item in items)


def create_regions(world: MassEffectAndromedaWorld) -> None:
    player = world.player
    names = list(data.TRAVEL_REGIONS) + list(data.SHIP_REGIONS)
    regions = {name: Region(name, player, world.multiworld) for name in names}
    world.multiworld.regions.extend(regions.values())

    tempest = regions["Tempest"]
    start_region = world.options.starting_region.current_key

    # Travel graph: from the Tempest, each destination needs its access item, and the
    # Nexus is free (it is where the campaign begins). Ship regions are always reachable.
    for item_name, region_name in data.ACCESS_ITEMS.items():
        if region_name == start_region:
            requirement = ()
        elif item_name == "Nexus Access":
            requirement = ()
        else:
            requirement = (item_name,)
        if requirement:
            tempest.connect(regions[region_name], f"Tempest -> {region_name}",
                            lambda state, req=requirement: _requires(state, player, *req))
        else:
            tempest.connect(regions[region_name], f"Tempest -> {region_name}")

    # The prologue is part of the opening state, never gated.
    tempest.connect(regions["Hyperion"], "Tempest -> Hyperion")

    for ship_region in data.SHIP_REGIONS:
        tempest.connect(regions[ship_region], f"Tempest -> {ship_region}")

    for loc in world.included_locations:
        location = MassEffectAndromedaLocation(player, loc.name, data.LOCATION_NAME_TO_ID[loc.name],
                                               regions[loc.region])
        regions[loc.region].locations.append(location)

    # The goal sits in Meridian: completing the Meridian finale is the win condition.
    victory_region = regions["Meridian"]
    event = MassEffectAndromedaLocation(player, data.VICTORY_EVENT, None, victory_region)
    event.place_locked_item(MassEffectAndromedaItem(data.VICTORY_EVENT, ItemClassification.progression,
                                                   None, player))
    victory_region.locations.append(event)
