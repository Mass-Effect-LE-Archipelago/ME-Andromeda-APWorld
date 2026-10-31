from __future__ import annotations

from typing import TYPE_CHECKING

from . import data

if TYPE_CHECKING:
    from .world import MassEffectAndromedaWorld


def set_rules(world: MassEffectAndromedaWorld) -> None:
    player = world.player
    multiworld = world.multiworld

    # The Meridian victory check needs the Meridian story gate on top of the region access.
    victory = multiworld.get_location(data.VICTORY_EVENT, player)
    world.set_rule(victory, lambda state: state.has("Priority Op: Meridian", player)
                   and state.can_reach_region("Meridian", player))

    multiworld.completion_condition[player] = lambda state: state.has(data.VICTORY_EVENT, player)
