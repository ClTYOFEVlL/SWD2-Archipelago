import copy
import re
import xml.etree.ElementTree as ET

from ..data import LocationData
from . import flags

UPGRADES = "Definitions/upgrades.xml"
OUTSETS = "Definitions/outsets.xml"
QUESTS = "Definitions/quests.xml"
COLLECTORS = "Definitions/collectors.xml"
OBJECTS = "Definitions/entities.objects.xml"
PICKUPS = "Definitions/entities.pickups.xml"
TEXTITEMS = "Definitions/textitems.xml"
DAMAGE_TYPES = "Definitions/damage_types.xml"

COG_CONTAINER = "ap_cog_container"  # a cog container whose drop gives nothing
PICKUP = "ap_pickup"  # a cog pickup with 0 cogs, so it gives nothing

CARTOGRAPHER_REWARDS = 8

# Their skip-ahead would complete the Fen quests from an early item
NO_SKIP_AHEAD = (
    "quest_sell_resources",
    "quest_fix_lamp",
    "quest_lit_the_lamp",
    "quest_get_jackhammer",
    "quest_find_teleporter",
)

# What hides the tools own rows in the Cog Mods tab, and how many the vanilla file has. 
# Items arrive in any order so a received tool would stay hidden behind them
TOOL_ROW_GATES = {
    "\t\t<HideUntilLevel>3</HideUntilLevel>\n": 1,
    '\t\t\t<Prerequisite Upgrade="lamp" Tier="2" />\n': 8,
    "\t\t\t<RequireWaterEnabled>true</RequireWaterEnabled>\n": 5,
}


def _xml(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def upgrades(text: str, locations: list[LocationData]) -> bytes:
    end = "</UpgradeDefinitions>"
    if text.count(end) != 1:
        raise ValueError("upgrades.xml: no single </UpgradeDefinitions>")

    text = text.replace("\r\n", "\n")
    for gate, count in TOOL_ROW_GATES.items():
        if text.count(gate) != count:
            raise ValueError(f"upgrades.xml: {text.count(gate)} of {gate.strip()}, expected {count}")
        text = text.replace(gate, "")

    new_definitions = flags.all_definitions(text, locations)
    return text.replace(end, new_definitions + end).encode("utf-8")


def outsets(text: str) -> bytes:
    """New games start with the Broken Lamp, the save marker and every shop chain at tier 1."""
    root = ET.fromstring(text)
    new_game = next(outset for outset in root.iter("Outset") if outset.get("Name") == "new_game")

    lamp = next(upgrade for upgrade in new_game.findall("Upgrade") if upgrade.get("Name") == "lamp")
    if lamp.get("Tier") != "2":
        raise ValueError(f"outsets.xml: new_game lamp tier is {lamp.get('Tier')}, expected 2")
    lamp.set("Tier", "1")

    ET.SubElement(new_game, "Upgrade", {"Name": "ap_save", "Tier": str(flags.PATCH_VERSION)})
    for tool in flags.TOOLS:
        ET.SubElement(new_game, "Upgrade", {"Name": flags.shop_flag(tool), "Tier": "1"})

    return _xml(root)


def quests(text: str) -> bytes:
    root = ET.fromstring(text)
    quest = {element.get("Name"): element for element in root.iter("Quest")}

    for name in NO_SKIP_AHEAD:
        skip_ahead = quest[name].find("AllowSkipAhead")
        if skip_ahead is None:
            raise ValueError(f"quests.xml: {name} has no AllowSkipAhead")
        quest[name].remove(skip_ahead)

    quest["quest_find_fen"].set("Template", "SIDE_QUEST")
    quest["quest_find_fen"].remove(quest["quest_find_fen"].find("UnlockedBy"))
    quest["quest_release_fen"].set("Template", "SIDE_QUEST")

    exit_temple = quest["quest_exit_temple"].find("UnlockedBy")
    if exit_temple.text != "quest_release_fen":
        raise ValueError(f"quests.xml: quest_exit_temple follows {exit_temple.text}")
    exit_temple.text = "quest_get_run_boots"

    return _xml(root)


def collectors(text: str, locations: list[LocationData]) -> bytes:
    rewards = sorted(
        (location for location in locations if location.type == "cartographer"),
        key=lambda location: int(location.entity),
    )
    flag_of_next = iter(reward.flag for reward in rewards)

    patched, count = re.subn(r'Blueprint="[^"]+"', lambda _: f'Blueprint="{next(flag_of_next)}"', text)
    if count != CARTOGRAPHER_REWARDS or len(rewards) != CARTOGRAPHER_REWARDS:
        raise ValueError(f"collectors.xml: {count} rewards for {len(rewards)} locations, expected 8")

    return patched.encode("utf-8")


def _variant(text: str, source_name: str, new_name: str, tweak) -> bytes:
    root = ET.fromstring(text)
    source = next(entity for entity in root.iter("Entity") if entity.get("Name") == source_name)

    new = copy.deepcopy(source)
    new.set("Name", new_name)
    tweak(new)
    root.append(new)

    return _xml(root)


def objects(text: str) -> bytes:
    # Removing the drop instead crashes the game
    def drop_empty_pickup(entity):
        entity.find("Drop/DropEntity").text = PICKUP

    return _variant(text, "upgrade_cog_container", COG_CONTAINER, drop_empty_pickup)


def pickups(text: str) -> bytes:
    def give_nothing(entity):
        entity.find("Pickup/UpgradeCogs").text = "0"

    return _variant(text, "pickup_upgrade_cog", PICKUP, give_nothing)


def damage_types(text: str) -> bytes:
    root = ET.fromstring(text)
    fire = next(damage for damage in root.iter("DamageType") if damage.get("Name") == "fire")
    boss = next(
        multiplier
        for multiplier in fire.iter("Multiplier")
        if multiplier.get("AgainstArmor") == "priest_glorious"
    )

    if boss.get("Value") != "0.05":
        raise ValueError(f"damage_types.xml: fire vs priest_glorious is {boss.get('Value')}, expected 0.05")
    boss.set("Value", "1")

    return _xml(root)


def textitems(text: str) -> bytes:
    logo = (
        '\t<TextItem Name="ap_logo_atlas" Template="BASE">\n'
        "\t\t<Scale>0.35</Scale>\n"
        f"\t\t<Image>{flags.ICON}</Image>\n"
        "\t</TextItem>\n"
    )

    end = text.rindex("</")
    return (text[:end] + logo + text[end:]).encode("utf-8")
