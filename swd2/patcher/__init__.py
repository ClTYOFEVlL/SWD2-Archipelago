"""Builds the data patch from the player's own game files and installs it as loose files under the game's
Bundle folder. The game must restart after it changes, and it takes full effect on a New Game."""
import json
import pathlib

from ..data import LOCATIONS
from . import atlas, definitions, levels
from .flags import PATCH_VERSION
from .gamefiles import GameFiles, read_z, write_z

STATE_DIR = "swd2ap_patch"
MANIFEST = "manifest.json"


def build(game_dir: str | pathlib.Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Returns the new files and the replaced ones, both as {path under Bundle: bytes}."""
    with GameFiles(game_dir) as files:
        written = {
            definitions.UPGRADES: definitions.upgrades(files.text(definitions.UPGRADES), LOCATIONS),
            definitions.OUTSETS: definitions.outsets(files.text(definitions.OUTSETS)),
            definitions.QUESTS: definitions.quests(files.text(definitions.QUESTS)),
            definitions.COLLECTORS: definitions.collectors(files.text(definitions.COLLECTORS), LOCATIONS),
            definitions.OBJECTS: definitions.objects(files.text(definitions.OBJECTS)),
            definitions.PICKUPS: definitions.pickups(files.text(definitions.PICKUPS)),
            definitions.TEXTITEMS: definitions.textitems(files.text(definitions.TEXTITEMS)),
            definitions.DAMAGE_TYPES: definitions.damage_types(files.text(definitions.DAMAGE_TYPES)),
        }
        written.update(atlas.files())

        replaced = {}
        for path, data in levels.patch_all(files, LOCATIONS).items():
            # The first part of the Temple exists only as a loose file, so it gets replaced
            if path == levels.TEMPLE:
                replaced[path + ".z"] = write_z(data)
            else:
                written[path] = data

        atlas_map = read_z((files.bundle / atlas.MAP).read_bytes())
        replaced[atlas.MAP] = write_z(atlas.patched_map(atlas_map))

    return written, replaced


def status(game_dir: str | pathlib.Path) -> dict | None:
    manifest = pathlib.Path(game_dir) / STATE_DIR / MANIFEST
    if not manifest.is_file():
        return None

    return json.loads(manifest.read_text(encoding="utf-8"))


def install(game_dir: str | pathlib.Path, log=print) -> None:
    game = pathlib.Path(game_dir)
    bundle = game / "Bundle"
    written, replaced = build(game)

    clashes = [path for path in written if (bundle / path).exists()]
    if clashes:
        raise FileExistsError("these loose files already exist (another mod or an old patch?): " + ", ".join(clashes))

    for path, data in {**written, **replaced}.items():
        target = bundle / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    state = game / STATE_DIR
    state.mkdir(exist_ok=True)
    (state / MANIFEST).write_text(json.dumps({"version": PATCH_VERSION}, indent=1), encoding="utf-8")
    log(f"patch installed: {len(written)} files written, {len(replaced)} replaced")
