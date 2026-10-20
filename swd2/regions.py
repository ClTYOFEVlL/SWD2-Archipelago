from typing import TYPE_CHECKING

from BaseClasses import Region

from . import notation
from .data import LOGIC
from .items import SWD2Item
from .locations import SWD2Location
from .money import money_events

if TYPE_CHECKING:
    from . import SWD2World

START = "Start"  # the fall into the Temple and the start ledge, "start" in the logic table
GOAL = "Rosie"


def _named_atoms() -> set[str]:
    rules = [location.rules for location in LOGIC.locations.values()]
    rules += [event.rules for event in LOGIC.events]
    rules += [row.rules for row in LOGIC.money]
    rules += [seller.rules for seller in LOGIC.sellers.values()]
    rules += list(LOGIC.region_rules.values())

    return {atom for variants in rules for text in variants.values() for atom in notation.atoms(notation.parse(text))}


# The parts of the Fire Temple's gates are already in their gates' rules, so they need no events
NAMED_ATOMS = _named_atoms()
EVENTS = [event for event in LOGIC.events if event.name == GOAL or event.name in NAMED_ATOMS]


def create_regions(world: "SWD2World") -> None:
    regions = {START: Region(START, world.player, world.multiworld)}

    for data in LOGIC.regions:
        if data.name.startswith("Trials") and not world.options.hell_cave_locations:
            continue

        # A region without a rule has nothing in it (Trials - Gauntlet)
        if world.variant in LOGIC.region_rules.get(data.name, {}):
            regions[data.name] = Region(data.name, world.player, world.multiworld)

    world.multiworld.regions += regions.values()

    for source, target in LOGIC.links:
        source = START if source == "start" else source
        if source in regions and target in regions:
            regions[source].connect(regions[target], f"{source} -> {target}")


def create_events(world: "SWD2World") -> None:
    for event in EVENTS:
        _add_event(world, event.name, event.region)

    for event in money_events(world.variant):
        _add_event(world, event.name, event.region)


def _add_event(world: "SWD2World", name: str, region: str) -> None:
    world.get_region(region).add_event(name, location_type=SWD2Location, item_type=SWD2Item, show_in_spoiler=False)
