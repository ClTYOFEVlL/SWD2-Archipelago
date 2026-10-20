from dataclasses import dataclass
from fractions import Fraction
from math import ceil

from .data import LOCATIONS, LOGIC

MONEY = "SWD2 Money"  # the counter in the collection state, not a real item
SHOP_TYPES = ("workbench", "carson", "clifford")
FRACTION_DUG = {"hard": Fraction(85, 100), "normal": Fraction(65, 100), "easy": Fraction(50, 100)}


@dataclass(frozen=True)
class MoneyEvent:
    name: str
    region: str
    base: int  # what its ore sells for at vanilla prices
    rule: str


def scaled_price(vanilla: int, percent: int) -> int:
    # Halves round up
    return max(1, (vanilla * percent + 50) // 100)


def shop_prices(percent: int) -> dict[str, int]:
    return {
        location.name: scaled_price(location.price, percent)
        for location in LOCATIONS
        if location.type in SHOP_TYPES
    }


def money_events(variant: str) -> list[MoneyEvent]:
    events = []
    names = set()

    for row in LOGIC.money:
        name = f"Money: {row.region}"
        number = 2
        while name in names:
            name = f"Money: {row.region} ({number})"
            number += 1

        names.add(name)
        events.append(MoneyEvent(name, row.region, row.base, row.rules[variant]))

    return events


def needed_money(prices: dict[str, int], difficulty: str, total: int) -> dict[str, int]:
    """The base money each shop slot needs: enough ore to have paid for every slot at least as cheap, when only a
    fraction of it gets dug and sold."""
    fraction = FRACTION_DUG[difficulty]
    needed = {}

    for name, price in prices.items():
        cumulative = sum(other for other in prices.values() if other <= price)
        needed[name] = min(ceil(cumulative / fraction), total)

    return needed
