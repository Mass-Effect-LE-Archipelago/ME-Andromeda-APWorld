from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification

from . import data

if TYPE_CHECKING:
    from .world import MassEffectAndromedaWorld


class MassEffectAndromedaItem(Item):
    game = data.GAME_NAME


def create_item(world: MassEffectAndromedaWorld, name: str) -> MassEffectAndromedaItem:
    if name in data.ACCESS_ITEMS or name in data.MISSION_ACCESS:
        classification = ItemClassification.progression
    elif name in data.WEAPONS:
        classification = ItemClassification.useful
    elif name == data.VICTORY_EVENT:
        classification = ItemClassification.progression
    else:
        classification = ItemClassification.filler
    return MassEffectAndromedaItem(name, classification, data.ITEM_NAME_TO_ID[name], world.player)


def create_items(world: MassEffectAndromedaWorld) -> None:
    pool: list[str] = []
    # Access: every region is opened by an item except the start region and the ship regions.
    for name in data.ACCESS_ITEMS:
        pool.append(name)
    for name in data.MISSION_ACCESS:
        pool.append(name)
    if world.options.weapon_items:
        pool.extend(data.WEAPONS)

    slots = len(world.included_locations)
    if len(pool) > slots:
        raise RuntimeError(f"{world.player_name}: {len(pool)} progression items do not fit in {slots} locations")
    world.multiworld.itempool.extend(world.create_item(name) for name in pool)
    filler_count = slots - len(pool)
    world.multiworld.itempool.extend(world.create_item(world.get_filler_item_name()) for _ in range(filler_count))
