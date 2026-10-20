from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification
from Options import OptionError

from .data import BASE_ID, ITEMS
from .money import scaled_price

if TYPE_CHECKING:
    from . import SWD2World

GAME = "SteamWorld Dig 2"

COG = "Upgrade Cog"
LAMP = "Progressive Lamp"
SPRINT = "Sprint Hydraulics"
JET = "Progressive Jet Engine"
SIGIL = "Sigillum Caelum et Infernum"

ITEM_TABLE = {item.name: item for item in ITEMS}
ITEM_NAME_TO_ID = {item.name: BASE_ID + item.id for item in ITEMS}
ITEM_NAME_GROUPS = {
    "Tools": {item.name for item in ITEMS if item.group == "tool"},
    "Blueprints": {item.name for item in ITEMS if item.group == "blueprint"},
    "Artifacts": {item.name for item in ITEMS if item.group == "artifact"},
    "Money Bundles": {item.name for item in ITEMS if item.group == "money"},
}
FILLER_WEIGHTS = {item.name: item.weight for item in ITEMS if item.group == "money"}
CLASSIFICATIONS = {
    "progression": ItemClassification.progression,
    "useful": ItemClassification.useful,
    "filler": ItemClassification.filler,
}


class SWD2Item(Item):
    game = GAME


def create_item(world: "SWD2World", name: str, progression: bool | None = None) -> SWD2Item:
    if progression is None:
        progression = world.progression_copies.get(name, 0) > 0

    item = ITEM_TABLE[name]
    classification = ItemClassification.progression if progression else CLASSIFICATIONS[item.classification]
    return SWD2Item(name, classification, ITEM_NAME_TO_ID[name], world.player)


def money_bundle(world: "SWD2World", name: str) -> int:
    vanilla = ITEM_TABLE[name].grant.vanilla
    return scaled_price(vanilla, world.options.shop_price_percent.value)


def precollect(world: "SWD2World") -> None:
    if world.options.logic_difficulty == world.options.logic_difficulty.option_easy:
        world.multiworld.push_precollected(create_item(world, LAMP))


def core_counts(world: "SWD2World") -> dict[str, int]:
    counts = {item.name: item.count for item in ITEMS if item.group not in ("cog", "money")}

    # Easy starts with one of the lamps
    if world.options.logic_difficulty == world.options.logic_difficulty.option_easy:
        counts[LAMP] -= 1

    for name in world.locked_items().values():
        counts[name] -= 1

    # The Sigil only opens the Trials
    if not world.options.hell_cave_locations:
        counts[SIGIL] = 0

    return counts


def cog_count(world: "SWD2World", free_slots: int, filler_items: int) -> int:
    """How many cogs go in the pool: cog_amount, or fewer if the excluded locations need more filler than is left."""
    cogs = min(world.options.cog_amount.value, free_slots)
    minimum = world.progression_copies.get(COG, 0)

    # Excluded locations only take filler, so cogs give way to money until there is enough
    excluded = len(world.options.exclude_locations.value & set(world.location_names_in_world))
    filler = free_slots - cogs + filler_items
    if excluded > filler:
        cogs -= excluded - filler

    if cogs < minimum:
        raise OptionError(
            f"{world.player_name}: {excluded} excluded locations need filler, but only "
            f"{free_slots - minimum + filler_items} filler items fit beside the {minimum} cogs logic needs."
        )

    return cogs


def progression_in_pool(world: "SWD2World", name: str) -> int:
    """How many of an item's copies in the pool must be progression: the ones logic needs, less those the player
    already owns. Copies from start_inventory_from_pool don't count, since AP takes them out of the pool later."""
    from_pool = world.options.start_inventory_from_pool.value.get(name, 0)
    locked = list(world.locked_items().values()).count(name)
    owned = world.start_counts.get(name, 0) - from_pool + locked
    return world.progression_copies.get(name, 0) - owned


def create_pool(world: "SWD2World", slots: int) -> list[SWD2Item]:
    pool = []
    for name, count in core_counts(world).items():
        needed = progression_in_pool(world, name)
        pool += [create_item(world, name, progression=i < needed) for i in range(count)]

    filler_items = sum(1 for item in pool if item.classification == ItemClassification.filler)
    cogs = cog_count(world, slots - len(pool), filler_items)
    needed = progression_in_pool(world, COG)
    pool += [create_item(world, COG, progression=i < needed) for i in range(cogs)]

    pool += [create_item(world, world.get_filler_item_name()) for _ in range(slots - len(pool))]
    return pool
