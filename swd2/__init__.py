from collections.abc import Mapping
from typing import Any

from BaseClasses import CollectionState, Item, Tutorial
from rule_builder.rules import Rule
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch as launch_component

from . import items, locations, notation, regions, rules
from .data import BASE_ID
from .money import MONEY, money_events, needed_money, shop_prices
from .options import OPTION_GROUPS, SWD2Options


def launch_client(*args: str) -> None:
    from .client import main
    launch_component(main, name="SWD2Client", args=args)


components.append(
    Component(
        "SteamWorld Dig 2 Client",
        func=launch_client,
        component_type=Type.CLIENT,
        game_name="SteamWorld Dig 2",
        supports_uri=True,
    )
)

EVENT_NAMES = {event.name for event in regions.EVENTS}

# The options the client and Universal Tracker read from slot data
SLOT_OPTIONS = (
    "logic_difficulty",
    "tricks",
    "shop_price_percent",
    "show_shop_items",
    "sprint_hydraulics",
    "teleporter_locations",
    "hell_cave_locations",
    "cog_amount",
)


class SWD2WebWorld(WebWorld):
    theme = "dirt"
    option_groups = OPTION_GROUPS
    tutorials: list[Tutorial] = []


class SWD2World(World):
    game = items.GAME
    web = SWD2WebWorld()
    options_dataclass = SWD2Options
    options: SWD2Options

    item_name_to_id = items.ITEM_NAME_TO_ID
    location_name_to_id = locations.LOCATION_NAME_TO_ID
    item_name_groups = items.ITEM_NAME_GROUPS
    location_name_groups = locations.LOCATION_NAME_GROUPS
    origin_region_name = regions.START

    # Universal Tracker can rebuild a seed from its slot data alone
    ut_can_gen_without_yaml = True

    # Which rules of the logic table this seed uses
    variant: str

    # Item name -> the most copies a rule asks for
    progression_copies: dict[str, int] = rules.copies_needed_by_any_variant()

    location_names_in_world: list[str]
    money_amounts: dict[str, int]  # money event -> its base dollars
    needed_money: dict[str, int]  # shop slot -> the base dollars it needs in logic
    start_counts: dict[str, int]  # the starting inventory

    def generate_early(self) -> None:
        # Universal Tracker: the options come from the seed's slot data
        passthrough = getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game)
        if passthrough:
            for name in SLOT_OPTIONS:
                getattr(self.options, name).value = passthrough["options"][name]

        difficulty = self.options.logic_difficulty.current_key
        logic_pass = "tricks" if self.options.tricks else "base"
        self.variant = f"{logic_pass}_{difficulty}"

        self.location_names_in_world = [location.name for location in locations.active_locations(self)]
        self.progression_copies = rules.copies_needed(self)
        self.money_amounts = {event.name: event.base for event in money_events(self.variant)}

        prices = shop_prices(self.options.shop_price_percent.value)
        total_money = sum(self.money_amounts.values())
        self.needed_money = needed_money(prices, difficulty, total_money)

    def create_regions(self) -> None:
        items.precollect(self)

        self.start_counts = {}
        for item in self.multiworld.precollected_items[self.player]:
            self.start_counts[item.name] = self.start_counts.get(item.name, 0) + 1

        regions.create_regions(self)
        locations.create_locations(self)
        regions.create_events(self)

        for location, item in self.locked_items().items():
            self.get_location(location).place_locked_item(self.create_item(item))

    def locked_items(self) -> dict[str, str]:
        """The podiums that keep their vanilla item, as location -> item. Their copies leave the pool."""
        # Vectron's exit saves you in the Mysterious Cave and only the Jet Engine gets you out
        locked = {locations.JET_PODIUM: items.JET}

        if self.options.sprint_hydraulics == self.options.sprint_hydraulics.option_vanilla:
            locked[locations.SPRINT_PODIUM] = items.SPRINT

        return locked

    def create_items(self) -> None:
        slots = len(self.multiworld.get_unfilled_locations(self.player))
        self.multiworld.itempool += items.create_pool(self, slots)

    def set_rules(self) -> None:
        rules.set_rules(self)

    def create_item(self, name: str) -> items.SWD2Item:
        return items.create_item(self, name)

    def get_filler_item_name(self) -> str:
        names = list(items.FILLER_WEIGHTS)
        weights = list(items.FILLER_WEIGHTS.values())
        return self.random.choices(names, weights=weights)[0]

    def rule_from_text(self, text: str) -> Rule:
        """Turns a rule from the logic table into a Rule Builder rule."""
        return notation.to_rule(notation.parse(text), EVENT_NAMES)

    # Money events add their dollars to a counter that shop slots check
    def collect(self, state: CollectionState, item: Item) -> bool:
        changed = super().collect(state, item)
        if changed and item.name in self.money_amounts:
            state.prog_items[self.player][MONEY] += self.money_amounts[item.name]

        return changed

    def remove(self, state: CollectionState, item: Item) -> bool:
        changed = super().remove(state, item)
        if changed and item.name in self.money_amounts:
            state.prog_items[self.player][MONEY] -= self.money_amounts[item.name]

        return changed

    def fill_slot_data(self) -> Mapping[str, Any]:
        prices = shop_prices(self.options.shop_price_percent.value)

        # Slot data goes through JSON, so the ids are strings
        prices_by_location = {str(self.location_name_to_id[name]): price for name, price in prices.items()}
        dollars_by_bundle = {
            str(self.item_name_to_id[name]): items.money_bundle(self, name)
            for name in items.FILLER_WEIGHTS
        }

        return {
            "options": self.options.as_dict(*SLOT_OPTIONS),
            "base_id": BASE_ID,
            "shop_prices": prices_by_location,
            "money_bundles": dollars_by_bundle,
            "death_link": bool(self.options.death_link),
        }

    @staticmethod
    def interpret_slot_data(slot_data: dict[str, Any]) -> dict[str, Any]:
        """Universal Tracker: hands the slot data back to generate_early."""
        return slot_data
