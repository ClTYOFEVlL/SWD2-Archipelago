import unittest
import xml.etree.ElementTree as ET

from BaseClasses import CollectionState, ItemClassification

from ..data import ITEMS
from ..patcher.definitions import DOOM_OBJECTIVE, all_generators, reactor_door
from ..patcher.flags import DEVICE_FLAGS
from .bases import SWD2TestBase

DEVICES = ["Device of Doom", "Device of Devastation", "Device of Disaster", "Device of Destruction"]
GENERATORS = [f"{device}: Generator" for device in DEVICES]


def everything_but(test: SWD2TestBase, name: str) -> CollectionState:
    state = CollectionState(test.multiworld)
    for item in test.multiworld.itempool:
        if item.name != name:
            state.collect(item, True)

    state.sweep_for_advancements()
    return state


class TestAllGenerators(SWD2TestBase):
    def test_pool(self):
        devices = [item for item in self.multiworld.itempool if item.name in DEVICES]
        self.assertEqual(sorted(item.name for item in devices), sorted(DEVICES))
        self.assertTrue(all(item.classification == ItemClassification.progression for item in devices))

    def test_generators_are_locations(self):
        self.assertEqual(sorted(self.world.location_name_groups["Generators"]), sorted(GENERATORS))
        for name in GENERATORS:
            self.multiworld.get_location(name, self.player)

    def test_goal_needs_every_device(self):
        for device in DEVICES:
            with self.subTest(device):
                state = everything_but(self, device)
                self.assertFalse(self.multiworld.has_beaten_game(state))

                state.collect(self.world.create_item(device))
                self.assertTrue(self.multiworld.has_beaten_game(state))


class TestVanillaGenerators(SWD2TestBase):
    options = {"generators_required": "vanilla"}

    def test_starts_with_doom(self):
        start = [item.name for item in self.multiworld.precollected_items[self.player]]
        self.assertEqual(start, ["Device of Doom"])

        in_pool = sorted(item.name for item in self.multiworld.itempool if item.name in DEVICES)
        self.assertEqual(in_pool, sorted(DEVICES[1:]))

    def test_doom_generator_is_still_a_location(self):
        self.multiworld.get_location("Device of Doom: Generator", self.player)


class TestReactorDoor(unittest.TestCase):
    def test_device_flags_match_the_items(self):
        grants = {item.name: item.grant.upgrade for item in ITEMS if item.group == "device"}
        self.assertEqual(grants, DEVICE_FLAGS)

    def test_objectives_wait_for_the_devices(self):
        quest = ET.fromstring(
            '<Quest Name="quest_destroy_the_last_generators">'
            '<Objective Name="obj_guidance_generator" Type="quest" Target="gen_3"/>'
            '<Objective Name="obj_yarrow_generator" Type="quest" Target="gen_1"/>'
            '<Objective Name="obj_firetemple_generator_2" Type="quest" Target="gen_2"/>'
            '<Pointer Objective="obj_guidance_generator"/>'
            "</Quest>"
        )
        reactor_door(quest)

        targets = {objective.get("Name"): objective.get("Target") for objective in quest.findall("Objective")}
        self.assertEqual(targets, {
            "obj_guidance_generator": "ap_device_devastation",
            "obj_yarrow_generator": "ap_device_disaster",
            "obj_firetemple_generator_2": "ap_device_destruction",
            DOOM_OBJECTIVE: "ap_device_doom",
        })
        self.assertTrue(all(objective.get("Type") == "upgrade_tier" for objective in quest.findall("Objective")))

        # Doom's objective sits with the others, before the pointers
        tags = [(element.tag, element.get("Name") or element.get("Objective")) for element in quest]
        self.assertEqual(tags[3], ("Objective", DOOM_OBJECTIVE))
        self.assertEqual(tags[-1], ("Pointer", DOOM_OBJECTIVE))

    def test_breaking_all_generators_cannot_complete_the_door(self):
        door = ET.fromstring(
            '<Quest Name="quest_destroy_the_last_generators"><UnlockedBy>quest_before</UnlockedBy></Quest>'
        )
        quest = ET.fromstring(
            '<Quest Name="quest_destroy_all_generators">'
            "<UnlockedBy>quest_destroy_the_last_generators</UnlockedBy>"
            "</Quest>"
        )
        all_generators(quest, door)

        self.assertEqual(quest.find("UnlockedBy").text, "quest_before")

    def test_all_generators_refuses_another_chain(self):
        door = ET.fromstring('<Quest Name="door"><UnlockedBy>quest_before</UnlockedBy></Quest>')
        quest = ET.fromstring('<Quest Name="all"><UnlockedBy>quest_other</UnlockedBy></Quest>')

        with self.assertRaises(ValueError):
            all_generators(quest, door)
