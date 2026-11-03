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


class OrbContainers(OptionSet):
    """
    Adds the chosen kinds of orb containers as locations.
    
    Health (23 Locations)
    Light (34 Locations)
    Mixed (23 Locations)
    Super (5 Locations)
    """
    display_name = "Orb Containers"
    valid_keys = {"Health", "Light", "Mixed", "Super"}


class SecretAreas(OptionSet):
    """
    Adds the chosen kinds of secrets as locations.

    Secret Areas - Hidden rooms. Most also hold a cog container or an artifact. (85 Locations)
    Mini Secrets - Small hidden notches that only chime. Many are a gem or a cog container's spot. (35 Locations)
    """
    display_name = "Secret Areas"
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
    pressure_bomb_items: PressureBombItems
    jackhammer_items: JackhammerItems
    jet_engine_items: JetEngineItems
    hook_items: HookItems
    grenade_items: GrenadeItems
    progressive_mobility: ProgressiveMobility
    generators_required: GeneratorsRequired
    teleporter_locations: TeleporterLocations
    hell_cave_locations: HellCaveLocations
    orb_containers: OrbContainers
    secret_areas: SecretAreas
    cog_amount: CogAmount
    filler_weights: FillerWeights
    start_inventory_from_pool: StartInventoryPool


OPTION_GROUPS = [
    OptionGroup("Goal", [GeneratorsRequired]),
    OptionGroup("Logic", [LogicDifficulty, Tricks]),
    OptionGroup("Shops", [ShopPricePercent, ShowShopItems]),
    OptionGroup("Locations", [TeleporterLocations, HellCaveLocations, OrbContainers, SecretAreas]),
    OptionGroup("Items", [SprintHydraulics, CogAmount, FillerWeights]),
    OptionGroup("Tool Items", [PressureBombItems, JackhammerItems, JetEngineItems, HookItems, GrenadeItems, ProgressiveMobility]),
]
