from .patcher.flags import TOOLS, shop_flag

LOGO = "{image ap_logo_atlas}"
MONEY = "{image money_small}"

TOOL_NAMES = {
    "pickaxe": "Pickaxe",
    "backpack": "Backpack",
    "lamp": "Lamp",
    "armor": "Armor",
    "watertank": "Water Tank",
    "pressurebomb": "Pressure Bomb",
    "jackhammer": "Jackhammer",
    "steampack": "Steam Jet",
}

SHOP_CATEGORY = "{tool} Slots"
SHOP_DESC = "Archipelago items for sale"
SHOP_SLOT_EMPTY = "(nothing bought yet)"
SHOP_SLOT_NAME = "%ITEM%"
SHOP_SLOT_DESC = f"{LOGO} An item from the multiworld ({{tool}} slot {{slot}})."

CARSON_OFFER = (
    f"So, how about it? You can have {LOGO} %NEXT:carson_cogs% "
    f"for only ${{var pricelist_next:carson_cogs}}{MONEY}."
)
CARSON_RETURN = f"Back for more {LOGO} Archipelago goods?"
CLIFFORD_OFFER = (
    f"For ${{var pricelist_next:blueprint_vendor_02}}{MONEY} I could part with "
    f"{LOGO} %NEXT:blueprint_vendor_02%. How about it?"
)
CLIFFORD_THINKING = (
    f"Still thinking about {LOGO} %NEXT:blueprint_vendor_02%? "
    f"Only ${{var pricelist_next:blueprint_vendor_02}}{MONEY}!"
)

CARTOGRAPHER_NEXT = (
    f"I will give you {LOGO} %NEXT:cartographer% if you can show me "
    "{var num_artifacts_threshold} artifacts {image artifacts_small} in total."
)
CARTOGRAPHER_REWARD = "To show you my appreciation, I shall hand you something from my stack."
CARTOGRAPHER_FLAG_DESC = "Cartographer reward {n}"

LOCATION_FLAG_NAME = "%ITEM%"
LOCATION_FLAG_DESC = f"{LOGO} An Archipelago check."

CONVERSATION_LINES = {
    "conversation_yx06g0_text": CARSON_OFFER,
    "conversation_0qym9q_text": CARSON_RETURN,
    "conversation_uxln27_text": CLIFFORD_OFFER,
    "conversation_dgw94e_text": CLIFFORD_THINKING,
    "conversation_rppjea_text": CARTOGRAPHER_NEXT,
    "conversation_tm2fum_text": CARTOGRAPHER_NEXT,
    "conversation_xkdvzp_text": CARTOGRAPHER_NEXT,
    "conversation_g8lzbu_text": CARTOGRAPHER_NEXT,
    "conversation_crg8xl_text": CARTOGRAPHER_NEXT,
    "conversation_p7vtak_text": CARTOGRAPHER_REWARD,
}


def shop_texts(tool: str, slot_count: int) -> dict[str, str]:
    chain = shop_flag(tool)
    tool_name = TOOL_NAMES[tool]

    # Tier 1 of a chain means nothing bought yet
    texts = {
        f"{chain}_cat": SHOP_CATEGORY.replace("{tool}", tool_name),
        f"{chain}_desc": SHOP_DESC,
        f"{chain}_1": SHOP_SLOT_EMPTY,
        f"{chain}_1_desc": "-",
    }

    for slot in range(1, slot_count + 1):
        texts[f"{chain}_{slot + 1}"] = SHOP_SLOT_NAME
        texts[f"{chain}_{slot + 1}_desc"] = SHOP_SLOT_DESC.replace("{tool}", tool_name).replace("{slot}", str(slot))

    return texts


def static_texts(slot_counts: dict[str, int]) -> dict[str, str]:
    texts = dict(CONVERSATION_LINES)

    for tool in TOOLS:
        texts.update(shop_texts(tool, slot_counts[tool]))

    for number in range(1, 9):
        texts[f"ap_loc_cartographer_{number}"] = LOCATION_FLAG_NAME
        texts[f"ap_loc_cartographer_{number}_desc"] = CARTOGRAPHER_FLAG_DESC.format(n=number)

    return texts
