from dataclasses import dataclass

from Options import (
    Choice,
    DeathLink,
    DefaultOnToggle,
    NamedRange,
    OptionCounter,
    OptionError,
    OptionGroup,
    PerGameCommonOptions,
    Range,
    StartInventoryPool,
    Toggle,
)


class LogicDifficulty(Choice):
    """
    What the logic expects of you.

    Hard - Only the tools a location can't be reached without, nothing extra for comfort.
    Shop expects you to sell about 85% of accessible ore.

    Normal - Also a pickaxe tier or two in heavy digging, some armor in hazard areas, Armor x2 for the final boss.
    Shop expects you to sell about 65% of accessible ore.

    Easy - About one tier more of the same tools, armor in every hazard area, a water tank in Fire Temple, and you start with a working lamp.
    Shop expects you to tell about 50% of accessible ore.
    """
    display_name = "Logic Difficulty"
    option_hard = 0
    option_normal = 1
    option_easy = 2
    default = option_normal


class Tricks(Toggle):
    """
    Puts movement tricks and sequence breaks in logic.
    Hook jumps, bomb and grenade jumps, several face switches in one climb, digging with Deathplosions, and any jump that needs precise timing.
    """
    display_name = "Tricks"


class ShopPricePercent(NamedRange):
    """
    Shop prices as a percentage of vanilla.
    Money bundles are scaled the same way.
    """
    display_name = "Shop Price Percent"
    range_start = 10
    range_end = 100
    default = 30
    special_range_names = {"vanilla": 100}


class ShowShopItems(DefaultOnToggle):
    """
    Shows each shop slot's item and who it is for.
    """
    display_name = "Show Shop Items"


class SprintHydraulics(Choice):
    """
    Where the Sprint Hydraulics are. 
    Almost everything needs them. Until they arrive you have only the Temple's first few checks.

    Shuffled - Anywhere in the multiworld.

    Vanilla - On their podium in the Temple of Guidance.
    """
    display_name = "Sprint Hydraulics"
    option_shuffled = 0
    option_vanilla = 1
    default = option_shuffled


class TeleporterLocations(DefaultOnToggle):
    """
    Unlocking each of the 25 teleporters (all but El Machino's) is a location. Fast travel still unlocks as usual.
    """
    display_name = "Teleporter Locations"


class HellCaveLocations(Toggle):
    """
    Adds the Trials (the hell caves) and their Proof of Completion. Their door needs the Sigillum Caelum et Infernum,
    which is only in the pool when this is on.
    """
    display_name = "Hell Cave Locations"


class CogAmount(Range):
    """
    How many Upgrade Cogs are in the pool. Logic never asks for more than 4.
    Cogs will only fill up to the number of locations available to them.
    """
    display_name = "Cog Amount"
    range_start = 4
    range_end = 84
    default = 84


class FillerWeights(OptionCounter):
    """
    Weights of various filler items.
    Setting one to 0 will disable it. 
    """
    display_name = "Filler Weights"
    min = 0
    default = {
        "Small Money Bundle": 50,
        "Medium Money Bundle": 35,
        "Large Money Bundle": 15,
    }
    valid_keys = default.keys()

    def verify_values(self) -> None:
        super().verify_values()

        if sum(self.value.values()) == 0:
            raise OptionError(f"For option {self.display_name}: at least one weight must be above 0.")


@dataclass
class SWD2Options(PerGameCommonOptions):
    death_link: DeathLink
    logic_difficulty: LogicDifficulty
    tricks: Tricks
    shop_price_percent: ShopPricePercent
    show_shop_items: ShowShopItems
    sprint_hydraulics: SprintHydraulics
    teleporter_locations: TeleporterLocations
    hell_cave_locations: HellCaveLocations
    cog_amount: CogAmount
    filler_weights: FillerWeights
    start_inventory_from_pool: StartInventoryPool


OPTION_GROUPS = [
    OptionGroup("Logic", [LogicDifficulty, Tricks]),
    OptionGroup("Shops", [ShopPricePercent, ShowShopItems]),
    OptionGroup("Locations", [TeleporterLocations, HellCaveLocations]),
    OptionGroup("Items", [SprintHydraulics, CogAmount, FillerWeights]),
]
