"""The patches to the level files. each location sets its hidden flag when found, plus a few story fixes."""
from ..data import LocationData
from . import script
from .definitions import COG_CONTAINER, PICKUP
from .flags import GOAL_FLAG, TEMPLE_LAMP_FLAG, VENDOR_REWARD_FLAG
from .gamefiles import GameFiles

HUB_MAIN = "Patchsets/TheHub/the_hub_patch_main.le"
VECTRON = "Patchsets/Archaea/archaea_cave_vectron_entrance.le"
SAVING_RUSTY = "Patchsets/TheHub/the_hub_cave_boss_saving_rusty.le"
TEMPLE = "Patchsets/TempleOfGuidance/temple_of_guidance.le"  # exists only as a loose .z file
EL_MACHINO = "Patchsets/ElMachino/el_machino.le"


def hook_gate(level: script.Level) -> None:
    """The game's own fallback opens Rosie's Storage on entering the Oasis once every generator is destroyed. It
    now waits for the Hook quest instead, so finishing the story past the Hook before Rosie's first talk can't leave
    Rosie's Storage shut until the end."""
    # OnEnterLevel -> CheckQuestState -> EnableEntity gate_hub_small
    check = level.node(32596016, "CheckQuestState")
    script.set_prop(check, "QuestName", "quest_get_grapplinghook", expect="quest_destroy_all_generators")


def vectron(level: script.Level) -> None:
    """Vectron's teleporter works after the first trip. It switches on whenever the cave loads, its checks also pass
    once the helper quest is done, and each load after the first trip gives Fen and the Map back. The trip takes
    them, and the vanilla game only gives them back in the exit scene of the first return."""
    # And(intro done, NOT entered, helper active): drop "NOT entered"
    script.drop_connection(level.node(32584767), 32584769)

    # The use checks: quest_vectron_helper IfActive, and obj_outro_conv IfUncompleted
    helper = level.node(32608341, "CheckQuestState")
    script.set_prop(helper, "IfCompleted", "True", expect="False")
    outro = level.node(32584758, "CheckObjectiveState")
    script.set_prop(outro, "IfCompleted", "True", expect="False")

    # On every load after the first trip: Fen, the Map and the teleporter
    enter = level.node(32584773, "OnEnterLevel")
    returned = level.add_node("CheckQuestState", "AP_ReturnCheck", [
        ("QuestName", "String", "quest_vectron_helper"),
        ("IfLocked", "Boolean", "False"),
        ("IfUnlocked", "Boolean", "False"),
        ("IfActive", "Boolean", "False"),
        ("IfReadyToComplete", "Boolean", "False"),
        ("IfCompleted", "Boolean", "True"),
    ])
    fen = level.set_upgrade("buddy", name="AP_ReturnFen")
    minimap = level.set_upgrade("minimap", name="AP_ReturnMap")
    teleporter_on = level.add_node("EnableEntity", "AP_ReturnTeleporter", [("Enable", "Boolean", "True")])
    script.bind(teleporter_on, 32586922)  # vectron_teleporter

    script.connect(enter, returned)
    script.connect(returned, fen)
    script.connect(fen, minimap)
    script.connect(minimap, teleporter_on)


def goal(level: script.Level) -> None:
    """Sets ap_goal when the saving-Rusty level starts, which only beating the final boss leads to."""
    enter = level.node(32584826, "OnEnterLevel")
    script.connect(enter, level.set_upgrade(GOAL_FLAG, name="AP_Goal"))


def lamp(level: script.Level) -> None:
    """The Temple no longer breaks the lamp: a New Game starts with the Broken Lamp, and received lamps must stay.
    The SetUpgrade lamp 1 node in the entry scene stays in its chain but sets a harmless hidden flag instead, since
    skipping the node left the scene stuck in testing."""
    breaker = level.node(32569662, "SetUpgrade")
    script.set_prop(breaker, "UpgradeId", TEMPLE_LAMP_FLAG, expect="lamp")
    script.set_prop(breaker, "HideNewMarker", "True", expect="False")


def shops(level: script.Level) -> None:
    """Carson's cog and Clifford's blueprint are no longer handed out: how many you bought from each price list is
    the check. Their reward nodes stay in their chains with nothing to give, since wiring the purchase past them
    froze the player after buying, like the Temple's lamp node."""
    # After Carson's PayForPriceListItem carson_cogs
    carson = level.node(32578539, "GiveValuables")
    script.set_prop(carson, "Cogs", "0", expect="1")
    script.set_prop(carson, "Silent", "True", expect="False")

    # After Clifford's PayForPriceListItem blueprint_vendor_02
    clifford = level.node(32579358, "GiveBlueprint")
    script.set_prop(clifford, "UpgradeId", VENDOR_REWARD_FLAG, expect="pressurebomb.launcher_triple")


STORY_PATCHES = {
    HUB_MAIN: [hook_gate],
    VECTRON: [vectron],
    SAVING_RUSTY: [goal],
    TEMPLE: [lamp],
    EL_MACHINO: [shops],
}


def patch_location(level: script.Level, location: LocationData) -> None:
    if location.type in ("teleporter", "secret_area", "secret_area_mini"):
        return

    flag = location.flag
    entity = level.entity(location.entity, location.layer)
    definition = entity.findtext("Definition")

    if location.type == "yonker":
        if definition != "GiveBlueprint":
            raise ValueError(f"{level.path}: {location.entity} is not a GiveBlueprint node")

        entity.find("Definition").text = "SetUpgrade"
        entity.find("Name").text = f"AP_Set_{flag}"
        for prop in entity.findall("Property"):
            entity.remove(prop)
        script.prop(entity, "UpgradeId", "String", flag)
        script.prop(entity, "Tier", "Int32", "1")
        script.prop(entity, "HideNewMarker", "Boolean", "True")
        return

    if location.type == "podium":
        script.set_prop(entity, "ActionParameter", flag, expect=location.vanilla)
        return

    if location.type == "cog":
        if definition != "upgrade_cog_container":
            raise ValueError(f"{level.path}: {location.entity} is {definition}, not a cog container")
        entity.find("Definition").text = COG_CONTAINER

    elif location.type == "artifact":
        if definition != "pickup_collectible":
            raise ValueError(f"{level.path}: {location.entity} is {definition}, not an artifact")
        entity.find("Definition").text = PICKUP
        entity.remove(script.get_prop(entity, "EditorPickup"))

    elif location.type not in ("superorb", "cryptium"):
        raise ValueError(f"unknown location type {location.type}")

    level.watch("OnDestroyed", location.entity, level.set_upgrade(flag), f"AP_On_{flag}")


def patch_all(files: GameFiles, locations: list[LocationData]) -> dict[str, bytes]:
    by_file = {}
    for location in locations:
        if location.file.endswith(".le"):
            by_file.setdefault(location.file, []).append(location)

    for path in STORY_PATCHES:
        by_file.setdefault(path, [])

    patched = {}
    for path, level_locations in sorted(by_file.items()):
        level = script.Level(files.text(path), path)

        # The story patches come first, so the ids of the nodes they add match the ones proven in testing
        for patch in STORY_PATCHES.get(path, ()):
            patch(level)

        for location in level_locations:
            patch_location(level, location)

        patched[path] = level.serialize()

    return patched
