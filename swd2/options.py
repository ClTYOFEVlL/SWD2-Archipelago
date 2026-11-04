from dataclasses import dataclass

from Options import (
    Choice,
    DeathLink,
    DefaultOnToggle,
    NamedRange,
    OptionCounter,
    OptionError,
    OptionGroup,
    OptionSet,
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


class ToolItems(Choice):
    option_progressive = 0
    option_main_item = 1


class PairItems(Choice):
    option_progressive = 0
    option_individual = 1


class PressureBombItems(ToolItems):
    """
    How the Pressure Bomb is given as items.

    Progressive - Four Progressive Pressure Bombs. The first gives the Pressure Bomb at tier 1, and each one after upgrades it a tier.

    Main Item - A Pressure Bomb and three Progressive Pressure Bombs. You need the Pressure Bomb to use the tool, and each Progressive Pressure Bomb upgrades it a tier.
    """
    display_name = "Pressure Bomb Items"
    default = ToolItems.option_progressive


class JackhammerItems(ToolItems):
    """
    How the Jackhammer is given as items.

    Progressive - Four Progressive Jackhammers. The first gives the Jackhammer at tier 1, and each one after upgrades it a tier.

    Main Item - A Jackhammer and three Progressive Jackhammers. You need the Jackhammer to use the tool, and each Progressive Jackhammer upgrades it a tier.
    """
    display_name = "Jackhammer Items"
    default = ToolItems.option_progressive


class JetEngineItems(ToolItems):
    """
    How the Jet Engine is given as items.

    Progressive - Three Progressive Jet Engines. The first gives the Jet Engine at tier 1, and each one after upgrades it a tier.

    Main Item - A Jet Engine and two Progressive Jet Engines. You need the Jet Engine to use the tool, and each Progressive Jet Engine upgrades it a tier.
    """
    display_name = "Jet Engine Items"
    default = ToolItems.option_progressive


class HookItems(PairItems):
    """
    How the Hook Shot and the Long-Range Grappler are given as items.

    Progressive - Two Progressive Hook Shots. The first gives the Hook Shot, the second the Long-Range Grappler.

    Individual - The Hook Shot and the Long-Range Grappler as two items. You still need the Hook Shot to use the Long-Range Grappler.
    """
    display_name = "Hook Items"
    default = PairItems.option_individual


class GrenadeItems(PairItems):
    """
    How the Grenade Launcher and the ThreeForce Grenade are given as items. Grenades need the Pressure Bomb either way.

    Progressive - Two Progressive Grenade Launchers. The first gives the Grenade Launcher, the second the ThreeForce Grenade.

    Individual - The Grenade Launcher and the ThreeForce Grenade as two items. You still need the Grenade Launcher to use the ThreeForce Grenade.
    """
    display_name = "Grenade Items"
    default = PairItems.option_individual


class ProgressiveMobility(Toggle):
    """
    Gives the Hook Shot, the Long-Range Grappler and the 3 Jet Engine items as one progressive item.

    Hook Items and Jet Engine Items options are ignored when this is enabled.
    """
    display_name = "Progressive Mobility"


class GeneratorsRequired(Choice):
    """
    Which generators the Reactor door needs.
    Each generator has a Device item, which counts as that generator destroyed.

    All - All four Devices.

    Vanilla - The three the vanilla door needs: Devastation, Disaster and Destruction. You start with the Device of Doom.
    """
    display_name = "Generators Required"
    option_all = 0
    option_vanilla = 1
    default = option_all


class Teleportersanity(DefaultOnToggle):
    """
    Adds every teleporter (except El Machino's) as locations. (25 Locations)
    Fast travel still unlocks as usual.
    """
    display_name = "Teleportersanity"


class IncludeTrials(Toggle):
    """
    Adds the Trials and their Proof of Completion. (1 Location)
    Their door needs the Sigillum Caelum et Infernum which is only in the pool when this is on.
    """
    display_name = "Include Trials"


class Orbsanity(OptionSet):
    """
    Adds the chosen kinds of orb containers as locations.

    Health (23 Locations)
    Light (34 Locations)
    Mixed (23 Locations)
    Super (5 Locations)
    """
    display_name = "Orbsanity"
    valid_keys = {"Health", "Light", "Mixed", "Super"}


class Secretsanity(OptionSet):
    """
    Adds the chosen kinds of secrets as locations.

    Secret Areas - Hidden rooms. Most also hold a cog container or an artifact. (85 Locations)
    Mini Secrets - Small hidden notches that only chime. Many are a gem or a cog container's spot. (35 Locations)
    """
    display_name = "Secretsanity"
    valid_keys = {"Secret Areas", "Mini Secrets"}


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


class TrapLink(Toggle):
    """
    Whether your received traps are linked to other players.
    A linked trap becomes the closest of your traps, unless its weight below is 0.
    """
    display_name = "Trap Link"


class TrapFillPercentage(NamedRange):
    """
    Replaces this percentage of filler with traps.
    """
    display_name = "Trap Fill Percentage"
    range_start = 0
    range_end = 100
    default = 0
    special_range_names = {
        "disabled": 0,
        "light": 10,
        "normal": 25,
        "extreme": 50,
    }


class TrapWeight(Range):
    range_start = 0
    range_end = 100
    default = 50


class LeakyTankTrapWeight(TrapWeight):
    """
    How often a trap is a Leaky Tank Trap, which empties your water tank.
    """
    display_name = "Leaky Tank Trap Weight"


class DarknessTrapWeight(TrapWeight):
    """
    How often a trap is a Darkness Trap, which empties your lamp.
    """
    display_name = "Darkness Trap Weight"


class GravityTrapWeight(TrapWeight):
    """
    How often a trap is a Gravity Trap, which increases your gravity.
    """
    display_name = "Gravity Trap Weight"


class FreezeTrapWeight(TrapWeight):
    """
    How often a trap is a Freeze Trap, which stops you from moving.
    """
    display_name = "Freeze Trap Weight"


class CutsceneTrapWeight(TrapWeight):
    """
    How often a trap is a Cutscene Trap, which makes Dorothy talk to herself.
    """
    display_name = "Cutscene Trap Weight"


class GravityTrapDuration(Range):
    """
    How many seconds a Gravity Trap lasts.
    """
    display_name = "Gravity Trap Duration"
    range_start = 1
    range_end = 60
    default = 15


class FreezeTrapDuration(Range):
    """
    How many seconds a Freeze Trap lasts.
    """
    display_name = "Freeze Trap Duration"
    range_start = 1
    range_end = 10
    default = 2


# Trap item -> its weight option
TRAP_WEIGHTS = {
    "Leaky Tank Trap": "leaky_tank_trap_weight",
    "Darkness Trap": "darkness_trap_weight",
    "Gravity Trap": "gravity_trap_weight",
    "Freeze Trap": "freeze_trap_weight",
    "Cutscene Trap": "cutscene_trap_weight",
}


@dataclass
class SWD2Options(PerGameCommonOptions):
    death_link: DeathLink
    trap_link: TrapLink
    generators_required: GeneratorsRequired
    logic_difficulty: LogicDifficulty
    tricks: Tricks
    include_trials: IncludeTrials
    teleportersanity: Teleportersanity
    orbsanity: Orbsanity
    secretsanity: Secretsanity
    sprint_hydraulics: SprintHydraulics
    cog_amount: CogAmount
    progressive_mobility: ProgressiveMobility
    pressure_bomb_items: PressureBombItems
    jackhammer_items: JackhammerItems
    jet_engine_items: JetEngineItems
    hook_items: HookItems
    grenade_items: GrenadeItems
    shop_price_percent: ShopPricePercent
    show_shop_items: ShowShopItems
    filler_weights: FillerWeights
    trap_fill_percentage: TrapFillPercentage
    leaky_tank_trap_weight: LeakyTankTrapWeight
    darkness_trap_weight: DarknessTrapWeight
    gravity_trap_weight: GravityTrapWeight
    freeze_trap_weight: FreezeTrapWeight
    cutscene_trap_weight: CutsceneTrapWeight
    gravity_trap_duration: GravityTrapDuration
    freeze_trap_duration: FreezeTrapDuration
    start_inventory_from_pool: StartInventoryPool


OPTION_GROUPS = [
    OptionGroup("Goal", [GeneratorsRequired]),
    OptionGroup("Logic", [LogicDifficulty, Tricks]),
    OptionGroup("Locations", [IncludeTrials, Teleportersanity, Orbsanity, Secretsanity]),
    OptionGroup("Items", [SprintHydraulics, CogAmount]),
    OptionGroup("Tool Items", [ProgressiveMobility, PressureBombItems, JackhammerItems, JetEngineItems, HookItems, GrenadeItems]),
    OptionGroup("Shops", [ShopPricePercent, ShowShopItems]),
    OptionGroup("Filler and Traps", [
        FillerWeights,
        TrapFillPercentage,
        LeakyTankTrapWeight,
        DarknessTrapWeight,
        GravityTrapWeight,
        FreezeTrapWeight,
        CutsceneTrapWeight,
        GravityTrapDuration,
        FreezeTrapDuration,
    ]),
]
