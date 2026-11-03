"""The messages between the client and the bridge."""
import zlib
from collections import Counter

from .data import BASE_ID, ITEMS, LOCATIONS, ItemData
from . import texts
from .patcher.definitions import CUTSCENE_COUNT
from .patcher.flags import GOAL_FLAG, shop_flag, waiting_icon

PORT = 23850  # the bridge listens on 127.0.0.1 only
PROTOCOL_VERSION = 2  # the bridge names its version in its hello

ITEMS_BY_ID = {BASE_ID + item.id: item for item in ITEMS}
ITEMS_BY_NAME = {item.name: item for item in ITEMS}

# Tool -> how many workbench slots it has
WORKBENCH_SLOTS = Counter(location.area for location in LOCATIONS if location.type == "workbench")

# The ways a report shows a location as found
_BY_FLAG = {location.flag: BASE_ID + location.id for location in LOCATIONS if location.flag}
_BY_TELEPORTER = {
    location.teleporter: BASE_ID + location.id
    for location in LOCATIONS
    if location.type == "teleporter"
}

# (the tool's chain flag, the tier the slot sells, location id)
_WORKBENCH = [
    (shop_flag(location.area), location.tier, BASE_ID + location.id)
    for location in LOCATIONS
    if location.type == "workbench"
]

# (price list, which purchase, location id)
_PRICE_LISTS = [
    (location.area, location.count, BASE_ID + location.id)
    for location in LOCATIONS
    if location.type in ("carson", "clifford")
]

# (artifacts needed, location id), in order
_CARTOGRAPHER = sorted(
    (location.threshold, BASE_ID + location.id)
    for location in LOCATIONS
    if location.type == "cartographer"
)


def seed_id(seed_name: str, slot: int) -> int:
    # 0 means "not bound yet"
    return zlib.crc32(f"{seed_name}:{slot}".encode()) or 1


def connect_message(seed: int) -> dict:
    return {"type": "connect", "seed": seed}


def disconnect_message() -> dict:
    return {"type": "disconnect"}


def grants(
    item_ids: list[int], money: dict[int, int], tool_items: list[ItemData], trap_seconds: dict[str, int]
) -> list[dict]:
    """How the bridge gives each received item. `money` holds each money bundle's dollars by item id, `tool_items`
    the main and progressive items of the seed's tool options, `trap_seconds` how long the traps that last a while do."""
    main_items = {item.grant.progressive: item.name for item in tool_items if item.grant.kind == "main"}
    copies = Counter()
    result = []

    for item_id in item_ids:
        item = ITEMS_BY_ID.get(item_id)
        if item is None:
            result.append({"kind": "none"})
            continue

        copies[item.name] += 1
        grant = item.grant

        if grant.kind == "trap":
            result.append({"kind": "trap", "trap": grant.trap, "amount": _trap_amount(grant.trap, trap_seconds)})

        # The main item sets the tier of every progressive copy received so far
        elif grant.kind == "main":
            progressive = ITEMS_BY_NAME[grant.progressive]
            result.append(_grant(progressive, copies[progressive.name] + 1, 0))

        # Progressive copies wait for their main item. "none" gives nothing but still shows the banner, with the
        # greyed icon of the tier the copy will count for
        elif item.name in main_items:
            if copies[main_items[item.name]]:
                result.append(_grant(item, copies[item.name] + 1, 0))
            else:
                tier = grant.first_tier + copies[item.name]
                result.append({"kind": "none", "icon": waiting_icon(grant.upgrade, tier)})

        # The n-th copy gives the n-th item named, as the copy of it that this is
        elif grant.kind == "progressive":
            given = grant.items[:copies[item.name]]
            result.append(_grant(ITEMS_BY_NAME[given[-1]], given.count(given[-1]), 0))

        else:
            result.append(_grant(item, copies[item.name], money.get(item_id, 0)))

    return result


def _trap_amount(trap: str, trap_seconds: dict[str, int]) -> int:
    return CUTSCENE_COUNT if trap == "cutscene" else trap_seconds.get(trap, 0)


def linked_trap_message(item_name: str, trap_seconds: dict[str, int]) -> dict:
    trap = ITEMS_BY_NAME[item_name].grant.trap
    return {"type": "trap", "trap": trap, "amount": _trap_amount(trap, trap_seconds)}


def _grant(item: ItemData, copy: int, dollars: int) -> dict:
    grant = item.grant
    if grant.kind == "upgrade":
        return {"kind": "upgrade", "upgrade": grant.upgrade, "tier": grant.first_tier + copy - 1}
    if grant.kind == "money":
        return {"kind": "money", "amount": dollars}
    if grant.kind == "blueprint":
        return {"kind": "blueprint", "upgrade": grant.upgrade}
    if grant.kind == "artifact":
        return {"kind": "artifact", "collectible": grant.collectible}

    return {"kind": "cog", "amount": grant.amount}


def plain(text: str) -> str:
    # The game reads {...} as markup
    return text.replace("{", "(").replace("}", ")")


def item_banner(finder: str, item: str, receiver: str, location: str) -> tuple[str, str]:
    if finder == receiver:
        first = f"{finder} found their {item}"
    else:
        first = f"{finder} sent {item} to {receiver}"

    return plain(first), plain(f"({location})")


def items_message(grant_list: list[dict], banners: list[tuple[str, str]], start: int, shown: int) -> dict:
    items = [
        {"grant": grant, "header": header, "text": text, "icon": grant.get("icon", "")}
        for grant, (header, text) in zip(grant_list[start:], banners[start:])
    ]
    return {"type": "items", "start": start, "shown": shown, "items": items}


def kill_message() -> dict:
    return {"type": "kill"}


def banner_message(header: str, text: str, icon: str = "") -> dict:
    return {"type": "banner", "header": plain(header), "text": plain(text), "icon": icon}


def prices_message(shop_prices: dict[int, int]) -> dict:
    chains = {}
    for chain, tier, location in _WORKBENCH:
        chains.setdefault(chain, {})[tier] = shop_prices[location]

    lists = {}
    for name, count, location in _PRICE_LISTS:
        lists.setdefault(name, {})[count] = shop_prices[location]

    return {
        "type": "prices",
        "upgrades": {chain: [tiers[tier] for tier in sorted(tiers)] for chain, tiers in chains.items()},
        "pricelists": {name: [counts[count] for count in sorted(counts)] for name, counts in lists.items()},
    }


def texts_message(names: dict[int, str]) -> dict:
    """The texts naming the items on offer"""
    result = texts.static_texts(WORKBENCH_SLOTS)

    for chain, tier, location in _WORKBENCH:
        key = f"{chain}_{tier}"
        result[key] = result[key].replace("%ITEM%", plain(names.get(location, "?")))

    for flag, location in _BY_FLAG.items():
        if location in names:
            result[flag] = texts.LOCATION_FLAG_NAME.replace("%ITEM%", plain(names[location]))
            result.setdefault(f"{flag}_desc", texts.LOCATION_FLAG_DESC)

    lists = {}
    for name, count, location in sorted(_PRICE_LISTS):
        lists.setdefault(name, []).append(plain(names.get(location, "?")))
    lists["cartographer"] = [plain(names.get(location, "?")) for _, location in _CARTOGRAPHER]

    return {"type": "texts", "texts": result, "lists": lists}


def found_locations(report: dict) -> set[int]:
    flags = report.get("flags", {})
    purchases = report.get("pricelists", {})

    found = {_BY_FLAG[flag] for flag in flags if flag in _BY_FLAG}
    found |= {location for chain, tier, location in _WORKBENCH if flags.get(chain, 0) >= tier}
    found |= {_BY_TELEPORTER[name] for name in report.get("teleporters", []) if name in _BY_TELEPORTER}
    found |= {location for name, count, location in _PRICE_LISTS if purchases.get(name, 0) >= count}
    return found


def goal_reached(report: dict) -> bool:
    return report.get("flags", {}).get(GOAL_FLAG, 0) > 0
