import xml.etree.ElementTree as ET

from ..data import LocationData

PATCH_VERSION = 1  # the patch's format, kept as ap_save's tier in every save the patch makes
SAVE_VERSION_TIERS = 16  # ap_save can hold versions 1 to 16
DIGIT_TIERS = 255  # ap_seed_* and ap_items_* each hold 0 to 255
SEED_FLAGS = [f"ap_seed_{i}" for i in range(4)]
ITEM_FLAGS = [f"ap_items_{i}" for i in range(2)]
TOOLS = ["pickaxe", "backpack", "lamp", "armor", "watertank", "pressurebomb", "jackhammer", "steampack"]
WORKBENCH_SLOTS = 42

ICON = "Icons/AP/ap_logo_atlas"  # the atlas entry the patch adds (atlas.py)
GOAL_FLAG = "ap_goal"
TEMPLE_LAMP_FLAG = "ap_temple_lamp"  # what the Temple's lamp-breaking node sets instead of the lamp (levels.py)
VENDOR_REWARD_FLAG = "ap_vendor_reward"  # what Clifford's sale gives instead of his blueprint (levels.py)


def shop_flag(tool: str) -> str:
    return f"ap_shop_{tool}"


def flag_upgrade(name: str, tiers: int = 1, icon: bool = True) -> str:
    tier = "\t\t<Tier>\n"
    if icon:
        tier += f"\t\t\t<Icon>{ICON}</Icon>\n"
    tier += f"\t\t\t<NameStringId>{name}</NameStringId>\n"
    tier += f"\t\t\t<DescStringId>{name}_desc</DescStringId>\n"
    tier += "\t\t</Tier>\n"

    return f'\t<Upgrade Name="{name}">\n' + tier * tiers + "\t</Upgrade>\n"


def paid_prices(upgrades_xml: str, tool: str) -> list[int]:
    # A tier that costs nothing is a starting or podium tier
    root = ET.fromstring(upgrades_xml)
    upgrade = next(upgrade for upgrade in root.iter("Upgrade") if upgrade.get("Name") == tool)

    costs = [int(tier.findtext("MoneyCost") or 0) for tier in upgrade.findall("Tier")]
    return [cost for cost in costs if cost > 0]


def shop_upgrade(tool: str, prices: list[int]) -> str:
    """The hidden ap_shop_<tool> chain. tier 1 is "nothing bought", tiers 2 and up are the slots."""
    name = shop_flag(tool)
    lines = [
        f'\t<Upgrade Name="{name}">',
        f"\t\t<CategoryStringId>{name}_cat</CategoryStringId>",
        f"\t\t<DescStringId>{name}_desc</DescStringId>",
        f"\t\t<NextLevelDescStringId>{name}_desc</NextLevelDescStringId>",
        "\t\t<UITierOffset>-1</UITierOffset>",
    ]

    for tier in range(1, len(prices) + 2):
        lines.append("\t\t<Tier>")
        if tier > 1:
            lines.append(f"\t\t\t<MoneyCost>{prices[tier - 2]}</MoneyCost>")
        lines.append(f"\t\t\t<Icon>{ICON}</Icon>")
        lines.append(f"\t\t\t<NameStringId>{name}_{tier}</NameStringId>")
        lines.append(f"\t\t\t<DescStringId>{name}_{tier}_desc</DescStringId>")
        lines.append("\t\t</Tier>")

    lines.append("\t</Upgrade>")
    return "\n".join(lines) + "\n"


def all_definitions(upgrades_xml: str, locations: list[LocationData]) -> str:
    definitions = [flag_upgrade(location.flag) for location in locations if location.flag]

    definitions.append(flag_upgrade(GOAL_FLAG, icon=False))
    definitions.append(flag_upgrade(TEMPLE_LAMP_FLAG, icon=False))
    definitions.append(flag_upgrade(VENDOR_REWARD_FLAG, icon=False))
    definitions.append(flag_upgrade("ap_save", SAVE_VERSION_TIERS, icon=False))
    for flag in SEED_FLAGS + ITEM_FLAGS:
        definitions.append(flag_upgrade(flag, DIGIT_TIERS, icon=False))

    slots = 0
    for tool in TOOLS:
        prices = paid_prices(upgrades_xml, tool)
        slots += len(prices)
        definitions.append(shop_upgrade(tool, prices))

    if slots != WORKBENCH_SLOTS:
        raise ValueError(f"{slots} workbench slots found, expected {WORKBENCH_SLOTS}")

    return "".join(definitions)
