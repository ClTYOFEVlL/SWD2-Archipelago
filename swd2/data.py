"""Loads the item, location and logic tables in data/."""
import json
import pkgutil
from dataclasses import dataclass
from typing import Any

BASE_ID = 0x5D2A_0000  # added to every id in the tables ("SD2A")

Rules = dict[str, str]  # variant -> rule


@dataclass(frozen=True)
class Grant:
    kind: str  # upgrade, blueprint, artifact, cog or money
    upgrade: str = ""
    first_tier: int = 0  # upgrades: the tier the first copy sets, with each later copy one more
    collectible: str = ""
    amount: int = 0  # cogs
    vanilla: int = 0  # money bundles: their dollars at vanilla prices


@dataclass(frozen=True)
class ItemData:
    id: int
    name: str
    group: str  # tool, blueprint, artifact, cog or money
    count: int  # copies in the pool
    logic: str | None  # its name in the rules, or None if no rule asks for it
    classification: str  # progression, useful or filler, for the copies no rule asks for
    grant: Grant
    weight: int = 0  # money bundles: how often each one is picked as filler


@dataclass(frozen=True)
class CogMod:
    upgrade: str
    name: str
    needs: str  # the tool it unlocks with
    count: int  # how many copies of that tool it takes
    cogs: int


@dataclass(frozen=True)
class LocationData:
    id: int
    name: str
    type: str  # cog, artifact, podium, workbench, teleporter and so on
    file: str
    area: str  # its area, or for a shop slot the tool or price list it belongs to
    layer: str
    entity: str
    flag: str = ""  # the hidden flag the patch sets when it's found
    vanilla: str = ""  # the game's id for the item it holds in the vanilla game
    threshold: int = 0  # Cartographer rewards: how many artifacts they need
    teleporter: str = ""
    price: int = 0  # vanilla
    tier: int = 0  # workbench slots: the tier of the tool's chain they sell
    count: int = 0  # Carson's and Clifford's slots: which purchase they are


@dataclass(frozen=True)
class LogicLocation:
    id: int
    name: str
    type: str
    region: str
    rules: Rules
    artifacts: int = 0


@dataclass(frozen=True)
class Seller:
    region: str
    rules: Rules


@dataclass(frozen=True)
class Event:
    name: str
    region: str
    rules: Rules


@dataclass(frozen=True)
class MoneyRow:
    region: str
    base: int  # what the ore sells for at vanilla prices
    rules: Rules


@dataclass(frozen=True)
class RegionData:
    name: str
    area: str


@dataclass(frozen=True)
class Logic:
    variants: list[str]
    regions: list[RegionData]
    links: list[tuple[str, str]]
    region_rules: dict[str, Rules]
    locations: dict[str, LogicLocation]  # by name, without the shop slots (they use their seller's rule)
    sellers: dict[str, Seller]
    events: list[Event]
    money: list[MoneyRow]


def _load(name: str) -> Any:
    return json.loads(pkgutil.get_data(__package__, f"data/{name}").decode("utf-8"))


def _item(row: dict) -> ItemData:
    row = dict(row, grant=Grant(**row["grant"]))
    row["classification"] = row.pop("class")  # "class" is taken in Python
    return ItemData(**row)


def _logic(table: dict) -> Logic:
    return Logic(
        variants=table["variants"],
        regions=[RegionData(**row) for row in table["regions"]],
        links=[(source, target) for source, target in table["links"]],
        region_rules=table["region_rules"],
        locations={row["name"]: LogicLocation(**row) for row in table["locations"]},
        sellers={name: Seller(**row) for name, row in table["npcs"].items()},
        events=[Event(**row) for row in table["events"]],
        money=[MoneyRow(**row) for row in table["money"]],
    )


_items = _load("items.json")
ITEMS = [_item(row) for row in _items["items"]]
COG_MODS = {name: CogMod(**row) for name, row in _items["mods"].items()}  # by their name in the rules
LOCATIONS = [LocationData(**row) for row in _load("locations.json")["locations"]]
LOGIC = _logic(_load("logic.json"))
