from BaseClasses import CollectionState
from Fill import distribute_items_restrictive
from test.general import gen_steps, setup_multiworld
from worlds.AutoWorld import call_all

from .. import SWD2World
from ..money import MONEY
from .bases import SWD2TestBase

YONKER_WEST = "West Desert - Intro: Zebulon Yonker's blueprint"
JET_2 = "El Machino: Workbench Jet Engine 2"
JET_PODIUM = "Mysterious Cave: Podium (Jet Engine)"
JET = "Progressive Jet Engine"


class TestNormal(SWD2TestBase):
    def test_shop_slots_need_money(self):
        state = CollectionState(self.multiworld)
        for item in self.multiworld.itempool:
            state.collect(item, True)

        location = self.multiworld.get_location(JET_2, self.player)
        self.assertEqual(state.prog_items[self.player][MONEY], 0)
        self.assertFalse(location.access_rule(state))

        state.sweep_for_advancements()
        self.assertEqual(state.prog_items[self.player][MONEY], sum(self.world.money_amounts.values()))
        self.assertTrue(location.access_rule(state))

    def test_money_needs(self):
        """At 30% the slots cost $6,564 together"""
        self.assertEqual(sum(self.world.fill_slot_data()["shop_prices"].values()), 6564)

        # The dearest slot: ceil(6564 / 0.65)
        self.assertEqual(self.world.needed_money[JET_2], 10099)

        # The cheapest two, Lamp 1 ($6 -> $2) and Backpack 1 ($8 -> $2): ceil(4 / 0.65)
        self.assertEqual(self.world.needed_money["El Machino: Workbench Lamp 1"], 7)

    def test_cartographer_counts_artifacts(self):
        artifacts = sorted(self.world.item_name_groups["Artifacts"])

        self.collect_by_name(["Sprint Hydraulics", *artifacts[:41]])
        self.assertTrue(self.can_reach_location("El Machino: Cartographer 28 artifacts"))
        self.assertFalse(self.can_reach_location("El Machino: Cartographer 42 artifacts"))

        self.collect_by_name(artifacts[41])
        self.assertTrue(self.can_reach_location("El Machino: Cartographer 42 artifacts"))


class TestEasy(SWD2TestBase):
    options = {"logic_difficulty": "easy"}

    def test_starts_with_a_lamp(self):
        start = [item.name for item in self.multiworld.precollected_items[self.player]]
        self.assertEqual(start, ["Progressive Lamp"])

        lamps = sum(1 for item in self.multiworld.itempool if item.name == "Progressive Lamp")
        self.assertEqual(lamps, 6)


class TestJetPodium(SWD2TestBase):
    options = {"logic_difficulty": "hard", "tricks": True}

    def test_jet_locked_on_its_podium(self):
        """The Mysterious Cave's podium keeps its Jet Engine since only the Jet gets you out"""
        location = self.multiworld.get_location(JET_PODIUM, self.player)
        self.assertTrue(location.locked)
        self.assertEqual(location.item.name, JET)

        pool = [item for item in self.multiworld.itempool if item.name == JET]
        self.assertEqual(len(pool), 2)

        progression = sum(1 for item in pool + [location.item] if item.advancement)
        self.assertEqual(progression, self.world.progression_copies[JET])


class TestStartInventory(SWD2TestBase):
    def test_start_items_dont_reach_yonkers_ledge(self):
        """The bridge gives nothing before falling into Temple of Guidance so items shouldn't reach the ledge"""
        self.collect_by_name("Progressive Jet Engine")
        self.assertFalse(self.can_reach_location(YONKER_WEST))

        self.collect_by_name("Sprint Hydraulics")
        self.assertTrue(self.can_reach_location(YONKER_WEST))

    def test_items_from_the_pool_keep_their_progression(self):
        for name in ("Progressive Pressure Bomb", "Progressive Armor"):
            with self.subTest(name):
                options = {"start_inventory_from_pool": {name: 1}}
                multiworld = setup_multiworld(SWD2World, gen_steps[:1], seed=7, options=options)

                # What AP's generator does: the item at the start, and its first copy in the pool swapped for filler
                multiworld.push_precollected(multiworld.create_item(name, 1))
                for step in gen_steps[1:]:
                    call_all(multiworld, step)

                pool = multiworld.itempool
                pool.remove(next(item for item in pool if item.name == name))
                pool.append(multiworld.worlds[1].create_filler())

                in_pool = sum(1 for item in pool if item.name == name and item.advancement)
                self.assertEqual(in_pool + 1, multiworld.worlds[1].progression_copies[name])

                distribute_items_restrictive(multiworld)
                self.assertTrue(multiworld.can_beat_game())


class TestUniversalTracker(SWD2TestBase):
    def test_regenerates_from_slot_data(self):
        options = {
            "logic_difficulty": "hard",
            "tricks": True,
            "teleporter_locations": False,
            "hell_cave_locations": True,
            "shop_price_percent": 55,
        }
        original = setup_multiworld(SWD2World, seed=5, options=options).worlds[1]

        multiworld = setup_multiworld(SWD2World, (), seed=6)
        multiworld.re_gen_passthrough = {SWD2World.game: original.fill_slot_data()}
        for step in gen_steps:
            call_all(multiworld, step)
        tracker = multiworld.worlds[1]

        self.assertEqual(tracker.variant, "tricks_hard")
        self.assertEqual(tracker.needed_money, original.needed_money)
        self.assertEqual(sorted(tracker.location_names_in_world), sorted(original.location_names_in_world))
