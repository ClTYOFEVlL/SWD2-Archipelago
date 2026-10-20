from typing import TYPE_CHECKING

from rule_builder.rules import Has, HasGroup

from . import notation
from .data import LOGIC, LocationData
from .locations import ALL_LOCATIONS, active_locations
from .money import MONEY, SHOP_TYPES, money_events
from .regions import EVENTS, GOAL

if TYPE_CHECKING:
    from . import SWD2World


def location_rule(location: LocationData, variant: str) -> str:
    if location.type in SHOP_TYPES:
        return LOGIC.sellers[location.type].rules[variant]

    return LOGIC.locations[location.name].rules[variant]


def set_rules(world: "SWD2World") -> None:
    variant = world.variant

    for location in active_locations(world):
        rule = world.rule_from_text(location_rule(location, variant))

        if location.type in SHOP_TYPES:
            rule = rule & Has(MONEY, world.needed_money[location.name])
        if location.type == "cartographer":
            rule = rule & HasGroup("Artifacts", location.threshold)

        world.set_rule(world.get_location(location.name), rule)

    for entrance in world.get_entrances():
        region_rules = LOGIC.region_rules[entrance.connected_region.name]
        world.set_rule(entrance, world.rule_from_text(region_rules[variant]))

    for event in EVENTS:
        world.set_rule(world.get_location(event.name), world.rule_from_text(event.rules[variant]))

    for event in money_events(variant):
        world.set_rule(world.get_location(event.name), world.rule_from_text(event.rule))

    world.set_completion_rule(Has(GOAL))


def copies_needed(world: "SWD2World") -> dict[str, int]:
    """The most copies of each item a rule of this seed asks for."""
    texts = [location_rule(location, world.variant) for location in active_locations(world)]
    texts += [event.rules[world.variant] for event in LOGIC.events]
    texts += [row.rules[world.variant] for row in LOGIC.money]

    counts = {}
    for text in texts:
        notation.needed_counts(notation.parse(text), counts)

    return counts


def copies_needed_by_any_variant() -> dict[str, int]:
    """The most copies of each item any rule of any variant asks for, for items created before generate_early."""
    rules = [LOGIC.locations[location.name].rules for location in ALL_LOCATIONS if location.name in LOGIC.locations]
    rules += [seller.rules for seller in LOGIC.sellers.values()]
    rules += [event.rules for event in LOGIC.events]
    rules += [row.rules for row in LOGIC.money]

    counts = {}
    for variants in rules:
        for text in variants.values():
            notation.needed_counts(notation.parse(text), counts)

    return counts
