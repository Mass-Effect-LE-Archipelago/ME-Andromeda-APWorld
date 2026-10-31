"""Generation tests: every option set fills and stays beatable across seeds.

Run from the Archipelago root with the world copied into `worlds/`:
    python -m pytest worlds/mass_effect_andromeda/test/test_generation.py -q
"""
from __future__ import annotations

from test.bases import WorldTestBase

from .. import data
from ..world import MassEffectAndromedaWorld as MEAWorld

WEAPON_SUFFIXES = ("assaultrifles", "pistols", "shotguns", "smgs", "sniperrifles")


class MEAWorldTestBase(WorldTestBase):
    game = "Mass Effect Andromeda"
    world: MEAWorld

    def beat(self) -> None:
        """Collect everything, then assert the seed can be finished."""
        self.collect_all_but([""])
        self.assertBeatable(True)


class TestDefaults(MEAWorldTestBase):
    def test_beatable_across_seeds(self) -> None:
        for seed in range(4):
            with self.subTest(seed=seed):
                self.world_setup(seed)
                self.beat()


class TestStartingRegions(MEAWorldTestBase):
    options = {"starting_region": "kadara"}

    def test_kadara_start(self) -> None:
        self.world_setup(0)
        self.beat()
        self.assertEqual(self.world.options.starting_region.current_key, "Kadara")


class TestNoWeaponItems(MEAWorldTestBase):
    options = {"weapon_items": False}

    def test_fewer_items(self) -> None:
        self.world_setup(0)
        self.beat()
        names = [item.name for item in self.multiworld.get_items()]
        weapon_items = [n for n in names if n.endswith(WEAPON_SUFFIXES)]
        self.assertEqual(weapon_items, [], "weapon items should be absent when the option is off")


class TestBoolChecksOnly(MEAWorldTestBase):
    options = {"bool_checks_only": True}

    def test_int_checks_excluded(self) -> None:
        self.world_setup(0)
        self.beat()
        slot = self.world.fill_slot_data()
        kinds = {d["kind"] for d in slot["detectors"]}
        self.assertEqual(kinds, {"bools"}, f"expected bool-only detectors, saw {kinds}")
        self.assertLess(len(slot["detectors"]), len(data.LOCATIONS))


class TestAllChecks(MEAWorldTestBase):
    options = {"bool_checks_only": False, "weapon_items": True}

    def test_full_pool_fits(self) -> None:
        self.world_setup(1)
        self.beat()
        self.assertEqual(len(self.world.included_locations), len(data.LOCATIONS))
        # the victory event is locked on its own event location, so the pool size matches the
        # non-event locations exactly
        self.assertEqual(len(self.multiworld.itempool), len(self.world.included_locations))
