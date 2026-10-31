from __future__ import annotations

from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, PerGameCommonOptions, Toggle


class StartingRegion(Choice):
    """Which destination is open from the start, besides the Tempest and the Nexus."""
    display_name = "Starting Region"
    option_eos = 0
    option_voeld = 1
    option_havarl = 2
    option_kadara = 3
    option_elaaden = 4
    option_aya = 5
    default = 0

    @property
    def current_key(self) -> str:
        return {"eos": "Eos", "voeld": "Voeld", "havarl": "Havarl", "kadara": "Kadara",
                "elaaden": "Elaaden", "aya": "Aya"}[self.current_option_name.lower()]


class WeaponItems(DefaultOnToggle):
    """Weapons found in the multiworld instead of only in the game's shops and research."""
    display_name = "Weapon Items"


class BoolChecksOnly(Toggle):
    """Only boolean plot flags become locations; integer counters stay out of the pool.

    Integer flags are detected as "value changed since the career was bound", which is a weaker
    signal than a boolean flipping true, so a seed can keep them out entirely.
    """
    display_name = "Boolean Checks Only"


@dataclass
class MassEffectAndromedaOptions(PerGameCommonOptions):
    starting_region: StartingRegion
    weapon_items: WeaponItems
    bool_checks_only: BoolChecksOnly
