"""The messages between the client and the bridge."""
import zlib
from collections import Counter

from .data import BASE_ID, ITEMS, LOCATIONS, ItemData
from . import texts
from .patcher.flags import GOAL_FLAG, shop_flag

PORT = 23850  # the bridge listens on 127.0.0.1 only
PROTOCOL_VERSION = 1  # the bridge names its version in its hello

ITEMS_BY_ID = {BASE_ID + item.id: item for item in ITEMS}

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


def grants(item_ids: list[int], money: dict[int, int]) -> list[dict]:
    """How the bridge gives each received item. `money` holds each money bundle's dollars by item id."""
    copies = Counter()
    result = []

    for item_id in item_ids:
        copies[item_id] += 1
        result.append(_grant(ITEMS_BY_ID.get(item_id), copies[item_id], money.get(item_id, 0)))

    return result


def _grant(item: ItemData | None, copy: int, dollars: int) -> dict:
    if item is None:
        return {"kind": "none"}

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
        {"grant": grant, "header": header, "text": text}
        for grant, (header, text) in zip(grant_list[start:], banners[start:])
    ]
    return {"type": "items", "start": start, "shown": shown, "items": items}


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
