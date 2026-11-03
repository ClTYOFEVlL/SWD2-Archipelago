import unittest
import xml.etree.ElementTree as ET
from collections import Counter

from BaseClasses import ItemClassification

from .. import bridge_protocol, texts
from ..items import ITEM_NAME_GROUPS, ITEM_NAME_TO_ID, MONEY_BUNDLES, TRAP_LINK_NAMES
from ..options import TRAP_WEIGHTS
from ..patcher.cutscenes import CUTSCENES
from ..patcher.definitions import CUTSCENE_COUNT, conversations, cutscene_line
from .bases import SWD2TestBase

TRAPS = ITEM_NAME_GROUPS["Traps"]


class TrapTestBase(SWD2TestBase):
    def pool_counts(self) -> Counter[str]:
        return Counter(item.name for item in self.multiworld.itempool)

    def count_of(self, names: set[str] | list[str]) -> int:
        counts = self.pool_counts()
        return sum(counts[name] for name in names)


class TestNoTrapsByDefault(TrapTestBase):
    def test_no_traps(self):
        self.assertEqual(self.count_of(TRAPS), 0)

    def test_every_trap_has_a_weight(self):
        self.assertEqual(set(TRAP_WEIGHTS), TRAPS)


class TestAllMoneyBecomesTraps(TrapTestBase):
    options = {"trap_fill_percentage": 100}

    def test_no_money_left(self):
        self.assertEqual(self.count_of(MONEY_BUNDLES), 0)
        self.assertGreater(self.count_of(TRAPS), 0)

    def test_classified_as_traps(self):
        for item in self.multiworld.itempool:
            if item.name in TRAPS:
                self.assertEqual(item.classification, ItemClassification.trap)


class TestSomeMoneyBecomesTraps(TrapTestBase):
    options = {"trap_fill_percentage": 50}

    def test_half(self):
        slots = self.count_of(MONEY_BUNDLES) + self.count_of(TRAPS)
        self.assertEqual(self.count_of(TRAPS), slots // 2)


class TestOneTrap(TrapTestBase):
    options = {
        "trap_fill_percentage": 100,
        "leaky_tank_trap_weight": 0,
        "darkness_trap_weight": 0,
        "gravity_trap_weight": 0,
        "cutscene_trap_weight": 0,
    }

    def test_only_that_trap(self):
        self.assertEqual(self.count_of(TRAPS), self.count_of(["Freeze Trap"]))


class TestAllWeightsZero(TrapTestBase):
    options = {"trap_fill_percentage": 100, **{option: 0 for option in TRAP_WEIGHTS.values()}}

    def test_money_stays(self):
        self.assertEqual(self.count_of(TRAPS), 0)
        self.assertGreater(self.count_of(MONEY_BUNDLES), 0)


class TestGrants(TrapTestBase):
    options = {"gravity_trap_duration": 30, "freeze_trap_duration": 5}

    def test_each_trap_reaches_the_bridge(self):
        for name in TRAPS:
            grant = bridge_protocol.grants([ITEM_NAME_TO_ID[name]], {}, [], {})[0]
            self.assertEqual(grant["kind"], "trap")
            self.assertTrue(grant["trap"])

    def test_the_durations_reach_the_bridge(self):
        seconds = self.world.fill_slot_data()["trap_seconds"]
        ids = [ITEM_NAME_TO_ID["Gravity Trap"], ITEM_NAME_TO_ID["Freeze Trap"], ITEM_NAME_TO_ID["Darkness Trap"]]
        amounts = [grant["amount"] for grant in bridge_protocol.grants(ids, {}, [], seconds)]
        self.assertEqual(amounts, [30, 5, 0])

    def test_the_cutscene_trap_knows_how_many_there_are(self):
        grant = bridge_protocol.grants([ITEM_NAME_TO_ID["Cutscene Trap"]], {}, [], {})[0]
        self.assertEqual(grant["amount"], CUTSCENE_COUNT)


class TestTrapLink(TrapTestBase):
    options = {"trap_link": True, "freeze_trap_weight": 0, "freeze_trap_duration": 5}

    def test_slot_data(self):
        slot_data = self.world.fill_slot_data()
        self.assertTrue(slot_data["trap_link"])
        self.assertEqual(slot_data["trap_weights"]["Freeze Trap"], 0)
        self.assertGreater(slot_data["trap_weights"]["Gravity Trap"], 0)

    def test_every_name_becomes_one_of_our_traps(self):
        self.assertEqual(set(TRAP_LINK_NAMES.values()), TRAPS)

    def test_a_linked_trap_reaches_the_bridge(self):
        message = bridge_protocol.linked_trap_message("Freeze Trap", {"freeze": 5})
        self.assertEqual(message, {"type": "trap", "trap": "freeze", "amount": 5})

        message = bridge_protocol.linked_trap_message("Cutscene Trap", {})
        self.assertEqual(message["amount"], CUTSCENE_COUNT)


class TestCutscenes(unittest.TestCase):
    def test_every_box_has_its_text(self):
        static = texts.static_texts(bridge_protocol.WORKBENCH_SLOTS)
        for number, lines in enumerate(CUTSCENES, 1):
            for line, text in enumerate(lines, 1):
                self.assertEqual(static[cutscene_line(number, line)], text)

    def test_the_lines_fit_and_close_their_markup(self):
        for lines in CUTSCENES:
            for line in lines:
                self.assertTrue(line.isascii())
                self.assertLessEqual(len(line), 124)  # the longest of Dorothy's own, with its markup
                self.assertEqual(line.count("{format "), 2 * line.count("{format reset}"))

    def test_the_patch_adds_them_for_dorothy(self):
        root = ET.fromstring(conversations('<Conversations><Conversation Name="a"/></Conversations>'))
        added = [node for node in root if node.get("Name") != "a"]
        self.assertEqual(len(added), CUTSCENE_COUNT)
        for node, lines in zip(added, CUTSCENES):
            speakers = [speak.get("Speaker") for speak in node.findall("Speak")]
            self.assertEqual(speakers, ["player"] * len(lines))
