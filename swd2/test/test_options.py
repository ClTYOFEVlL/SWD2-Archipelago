import itertools
import unittest

from BaseClasses import MultiWorld
from Fill import FillError, distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld

from .. import SWD2World
from ..locations import LOCATION_NAME_TO_ID
from ..options import FillerWeights
from .bases import SWD2TestBase

COMBINATIONS = list(itertools.product(
    ("hard", "normal", "easy"),  # logic_difficulty
    (False, True),  # tricks
    ("shuffled", "vanilla"),  # sprint_hydraulics
    (True, False),  # teleporter_locations
    (False, True),  # hell_cave_locations
))


def filled(options: dict, seed: int) -> MultiWorld:
    multiworld = setup_multiworld(SWD2World, seed=seed, options=options)
    distribute_items_restrictive(multiworld)
    return multiworld


class TestCombinations(unittest.TestCase):
    def test_every_combination_is_beatable(self):
        # AP's fill fails on a rare solo seed so such a seed gets one more try
        retries = 0

        for number, (difficulty, tricks, sprint, teleporters, trials) in enumerate(COMBINATIONS):
            options = {
                "logic_difficulty": difficulty,
                "tricks": tricks,
                "sprint_hydraulics": sprint,
                "teleporter_locations": teleporters,
                "hell_cave_locations": trials,
            }

            with self.subTest(**options):
                try:
                    multiworld = filled(options, number)
                except FillError:
                    retries += 1
                    multiworld = filled(options, number + 1000)

                self.assertTrue(multiworld.fulfills_accessibility())

        self.assertLessEqual(retries, 2)


class TestCogReduction(SWD2TestBase):
    # Without teleporters the only filler is the Yonker brothers 3 blueprints so 6 excluded locations turn 3 cogs into money
    options = {
        "teleporter_locations": False,
        "exclude_locations": [
            "El Machino: Workbench Pickaxe 1",
            "El Machino: Workbench Pickaxe 2",
            "El Machino: Workbench Lamp 1",
            "El Machino: Workbench Lamp 2",
            "El Machino: Trader Carson 1",
            "El Machino: Trader Carson 2",
        ],
    }

    def test_exclusions_replace_cogs(self):
        names = [item.name for item in self.multiworld.itempool]
        self.assertEqual(names.count("Upgrade Cog"), 84 - 3)
        self.assertEqual(sum(1 for name in names if name.endswith("Money Bundle")), 3)

    def test_too_many_exclusions_fail(self):
        options = {"teleporter_locations": False, "exclude_locations": list(LOCATION_NAME_TO_ID)}
        with self.assertRaises(OptionError):
            setup_multiworld(SWD2World, options=options)


class TestFillerWeights(SWD2TestBase):
    # Few cogs so most of the pool is filler
    options = {
        "cog_amount": 4,
        "filler_weights": {"Small Money Bundle": 0, "Large Money Bundle": 1},
    }

    def test_only_weighted_bundles(self):
        bundles = {item.name for item in self.multiworld.itempool if item.name.endswith("Money Bundle")}
        self.assertEqual(bundles, {"Large Money Bundle"})

    def test_all_zero_fails(self):
        weights = FillerWeights.from_any({"Small Money Bundle": 0})
        with self.assertRaises(OptionError):
            weights.verify_values()
