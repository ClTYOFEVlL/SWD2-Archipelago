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
INTRO = "Patchsets/WestDesert/west_desert_intro.le"


def intro(level: script.Level) -> None:
    """The opening cutscene is skipped."""
    # Checkpoint -> SetPosition -> FreezePlayerInput (the cutscene) ... UnfreezePlayerInput -> Delay -> move hint
    start = level.node(32581848, "SetPosition")
    script.drop_connection(start, 32566045)
    script.connect(start, level.node(32579542, "Delay"))


def temple_exit(level: script.Level) -> None:
    """Arriving in El Machino counts as leaving the Temple if that quest is still open, allowing the El Machino speech to play."""
    enter = level.add_node("OnEnterLevel", "AP_TempleExitEnter", [
        ("IfEnteredNormally", "Boolean", "True"),
        ("IfFastTraveled", "Boolean", "True"),
        ("IfLoadedGame", "Boolean", "True"),
        ("IfLoadedCheckpoint", "Boolean", "True"),
        ("IfRevived", "Boolean", "True"),
    ])
    still_open = level.add_node("CheckQuestState", "AP_TempleExitCheck", [
        ("QuestName", "String", "quest_exit_temple"),
        ("IfLocked", "Boolean", "False"),
        ("IfUnlocked", "Boolean", "False"),
        ("IfActive", "Boolean", "True"),
        ("IfReadyToComplete", "Boolean", "False"),
        ("IfCompleted", "Boolean", "False"),
    ])
    leave = level.add_node("ProgressQuest", "AP_TempleExit", [
        ("QuestName", "String", "quest_exit_temple"),
        ("ObjectiveName", "String", "obj_exit_temple"),
        ("Increase", "Int32", "1"),
    ])

    script.connect(enter, still_open)
    script.connect(still_open, leave)


def hook_gate(level: script.Level) -> None:
    """Rosie's Storage gate's fallback waits for the Hook quest instead of the last generators.
    Prevents Rosie's Storage from being shut until the end of the game."""
    # OnEnterLevel -> CheckQuestState -> EnableEntity gate_hub_small
    check = level.node(32596016, "CheckQuestState")
    script.set_prop(check, "QuestName", "quest_get_grapplinghook", expect="quest_destroy_all_generators")


def vectron(level: script.Level) -> None:
    """Vectron is skipped. Its teleporter stays off, a snake stone opens the Hall, and entering the cave is the trip."""
    # The intro scene that switches the teleporter on, and its use, both check quest_vectron_helper IfActive
    for check in (32608340, 32608341):
        script.set_prop(level.node(check, "CheckQuestState"), "IfActive", "False", expect="True")

    # A vertical snake piece instead of the chain's end cap at (31,5): its open end faces the room below
    tiles = level.layers["Foreground"]
    mappings = tiles.find("TileMappings")
    vertical = script.sub(mappings, "Mapping")
    vertical.set("Name", "snake_vertical_01")
    vertical.set("FlipX", "False")
    vertical.set("FlipY", "False")
    vertical.set("Rotation", "False")

    row = tiles.find("Tiles")[33]
    cells = row.text.split(" ")
    if cells[40] != "2":
        raise ValueError(f"{level.path}: tile (40,33) is {cells[40]}, expected the snake cap 2")
    cells[40] = str(len(mappings) - 1)
    row.text = " ".join(cells)

    # The exit scene completed quest_enter_vectron
    enter = level.node(32584773, "OnEnterLevel")
    active = level.add_node("CheckQuestState", "AP_VectronCheck", [
        ("QuestName", "String", "quest_enter_vectron"),
        ("IfLocked", "Boolean", "False"),
        ("IfUnlocked", "Boolean", "False"),
        ("IfActive", "Boolean", "True"),
        ("IfReadyToComplete", "Boolean", "False"),
        ("IfCompleted", "Boolean", "False"),
    ])
    complete = level.add_node("CompleteQuest", "AP_VectronDone", [("QuestName", "String", "quest_enter_vectron")])

    script.connect(enter, active)
    script.connect(active, complete)


def goal(level: script.Level) -> None:
    """Sets ap_goal when the saving-Rusty level starts, which only beating the final boss leads to."""
    enter = level.node(32584826, "OnEnterLevel")
    script.connect(enter, level.set_upgrade(GOAL_FLAG, name="AP_Goal"))


def lamp(level: script.Level) -> None:
    """The Temple's lamp-breaking node sets a hidden flag instead of breaking the lamp."""
    breaker = level.node(32569662, "SetUpgrade")
    script.set_prop(breaker, "UpgradeId", TEMPLE_LAMP_FLAG, expect="lamp")
    script.set_prop(breaker, "HideNewMarker", "True", expect="False")


def shops(level: script.Level) -> None:
    """Carson's and Clifford's reward nodes give nothing. The purchase counts are the checks."""
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
    EL_MACHINO: [shops, temple_exit],
    INTRO: [intro],
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

    elif location.type not in ("superorb", "mixedorb", "healthorb", "lightorb", "generator"):
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
