from typing import TYPE_CHECKING

from BaseClasses import Location

from .data import BASE_ID, LOCATIONS, LOGIC, LocationData
from .items import GAME
from .money import SHOP_TYPES

if TYPE_CHECKING:
    from . import SWD2World

# Secret areas, super orb containers and Cryptium are in the table but aren't locations yet
LOCATION_TYPES = ("cog", "artifact", "podium", "yonker", "cartographer", "teleporter") + SHOP_TYPES
EL_MACHINO_TELEPORTER = "elmachino_teleporter_01"  # unlocks by itself, so it isn't a location

SPRINT_PODIUM = "Temple of Guidance - Upper: Podium (Sprint Hydraulics)"
JET_PODIUM = "Mysterious Cave: Podium (Jet Engine)"


def _is_location(location: LocationData) -> bool:
    if location.type == "teleporter" and location.teleporter == EL_MACHINO_TELEPORTER:
        return False

    return location.type in LOCATION_TYPES


# Every location a seed can have
ALL_LOCATIONS = [location for location in LOCATIONS if _is_location(location)]

LOCATION_NAME_TO_ID = {location.name: BASE_ID + location.id for location in ALL_LOCATIONS}

_GROUPS = {
    "Cog Containers": "cog",
    "Artifacts": "artifact",
    "Podiums": "podium",
    "Yonker Brothers": "yonker",
    "Cartographer": "cartographer",
    "Workbench": "workbench",
    "Trader Carson": "carson",
    "Clifford": "clifford",
    "Teleporters": "teleporter",
}
LOCATION_NAME_GROUPS = {
    group: {location.name for location in ALL_LOCATIONS if location.type == kind}
    for group, kind in _GROUPS.items()
}
LOCATION_NAME_GROUPS["Shops"] = {location.name for location in ALL_LOCATIONS if location.type in SHOP_TYPES}


class SWD2Location(Location):
    game = GAME


def in_trials(location: LocationData) -> bool:
    """The Trials' only location is their Proof of Completion."""
    logic = LOGIC.locations.get(location.name)
    return logic is not None and logic.region.startswith("Trials")


def active_locations(world: "SWD2World") -> list[LocationData]:
    active = []

    for location in ALL_LOCATIONS:
        if location.type == "teleporter" and not world.options.teleporter_locations:
            continue
        if in_trials(location) and not world.options.hell_cave_locations:
            continue

        active.append(location)

    return active


def region_of(location: LocationData) -> str:
    if location.type in SHOP_TYPES:
        return LOGIC.sellers[location.type].region

    return LOGIC.locations[location.name].region


def create_locations(world: "SWD2World") -> None:
    for location in active_locations(world):
        region = world.get_region(region_of(location))
        region.locations.append(SWD2Location(world.player, location.name, LOCATION_NAME_TO_ID[location.name], region))
