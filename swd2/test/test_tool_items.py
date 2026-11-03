import itertools
import unittest

from Fill import FillError, distribute_items_restrictive
from test.general import setup_multiworld

from .. import SWD2World
from ..bridge_protocol import grants
from ..data import BASE_ID
from ..items import ITEM_TABLE, tool_option_items
from ..notation import atom_items
from .bases import SWD2TestBase

TOOL_OPTIONS = ("pressure_bomb_items", "jackhammer_items", "jet_engine_items", "hook_items", "grenade_items")


def ids(*names: str) -> list[int]:
    return [BASE_ID + ITEM_TABLE[name].id for name in names]


class TestAllChanged(SWD2TestBase):
    options = {
        "pressure_bomb_items": "main_item",
        "jackhammer_items": "main_item",
        "jet_engine_items": "main_item",
        "hook_items": "progressive",
        "grenade_items": "progressive",
    }

    def pool_count(self, name: str) -> int:
        return sum(1 for item in self.multiworld.itempool if item.name == name)

    def test_pool(self):
        expected = {
            "Pressure Bomb": 1, "Progressive Pressure Bomb": 3,
            "Jackhammer": 1, "Progressive Jackhammer": 3,
            "Jet Engine": 1, "Progressive Jet Engine": 2,
            "Progressive Hook Shot": 2, "Hook Shot": 0, "Long-Range Grappler": 0,
            "Progressive Grenade Launcher": 2, "Grenade Launcher": 0, "ThreeForce Grenade": 0,
        }
        self.assertEqual({name: self.pool_count(name) for name in expected}, expected)

        # Every copy a rule asks for is progression
        for name, needed in self.world.progression_copies.items():
            if name in ITEM_TABLE and name != "Upgrade Cog":
                progression = sum(1 for item in self.multiworld.itempool if item.name == name and item.advancement)
                self.assertEqual(progression, needed, name)

    def test_rules_name_the_seeds_items(self):
        tool_items = self.world.tool_items
        self.assertEqual(atom_items("Bomb", 1, tool_items), [("Pressure Bomb", 1)])
        self.assertEqual(atom_items("BusterShells", 1, tool_items),
                         [("Pressure Bomb", 1), ("Progressive Pressure Bomb", 2)])
        self.assertEqual(atom_items("Grappler", 1, tool_items), [("Progressive Hook Shot", 2)])
        self.assertEqual(atom_items("Launcher", 1, tool_items), [("Progressive Grenade Launcher", 1)])

    def test_progressive_copies_alone_do_nothing(self):
        self.collect_by_name(["Sprint Hydraulics", *["Progressive Pressure Bomb"] * 3])
        without = set(self.multiworld.get_reachable_locations(self.multiworld.state, self.player))
        self.collect_by_name("Pressure Bomb")
        self.assertLess(without, set(self.multiworld.get_reachable_locations(self.multiworld.state, self.player)))

    def test_slot_data_names_the_options(self):
        options = self.world.fill_slot_data()["options"]
        self.assertEqual(tool_option_items(options), self.world.tool_items)


class TestGrants(unittest.TestCase):
    main_bomb = tool_option_items({"pressure_bomb_items": 1})

    def test_progressive_copies_wait_for_the_main_item(self):
        received = ids("Progressive Pressure Bomb", "Progressive Pressure Bomb", "Pressure Bomb",
                       "Progressive Pressure Bomb")
        self.assertEqual(grants(received, {}, self.main_bomb), [
            {"kind": "none", "icon": "Icons/AP/waiting_pressurebomb_2"},
            {"kind": "none", "icon": "Icons/AP/waiting_pressurebomb_3"},
            {"kind": "upgrade", "upgrade": "pressurebomb", "tier": 3},
            {"kind": "upgrade", "upgrade": "pressurebomb", "tier": 4},
        ])

    def test_progressive_pairs(self):
        received = ids("Progressive Hook Shot", "Progressive Grenade Launcher", "Progressive Hook Shot",
                       "Progressive Grenade Launcher")
        tool_items = tool_option_items({"hook_items": 0, "grenade_items": 0})
        self.assertEqual(grants(received, {}, tool_items), [
            {"kind": "upgrade", "upgrade": "hook", "tier": 1},
            {"kind": "blueprint", "upgrade": "pressurebomb.launcher"},
            {"kind": "blueprint", "upgrade": "hook.long_hook"},
            {"kind": "blueprint", "upgrade": "pressurebomb.launcher_triple"},
        ])

    def test_default_items(self):
        result = grants(ids("Progressive Pressure Bomb", "Hook Shot"), {}, [])
        self.assertEqual(result, [
            {"kind": "upgrade", "upgrade": "pressurebomb", "tier": 1},
            {"kind": "upgrade", "upgrade": "hook", "tier": 1},
        ])


class TestCombinations(unittest.TestCase):
    def test_every_combination_generates(self):
        # AP's fill fails on a rare solo seed so such a seed gets one more try
        retries = 0

        tools = itertools.product(("progressive", "main_item"), repeat=3)
        pairs = itertools.product(("progressive", "individual"), repeat=2)
        for number, values in enumerate(itertools.product(tools, pairs)):
            options = dict(zip(TOOL_OPTIONS, values[0] + values[1]))

            with self.subTest(**options):
                try:
                    multiworld = setup_multiworld(SWD2World, seed=number, options=options)
                    distribute_items_restrictive(multiworld)
                except FillError:
                    retries += 1
                    multiworld = setup_multiworld(SWD2World, seed=number + 1000, options=options)
                    distribute_items_restrictive(multiworld)

                self.assertTrue(multiworld.fulfills_accessibility())

        self.assertLessEqual(retries, 2)
