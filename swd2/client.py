"""The SteamWorld Dig 2 Client: between the Archipelago server and the bridge in the game"""
import asyncio
import pathlib
import sys

import Utils
from CommonClient import (
    ClientCommandProcessor,
    CommonContext,
    get_base_parser,
    gui_enabled,
    handle_url_arg,
    logger,
    server_loop,
)
from MultiServer import mark_raw
from NetUtils import ClientStatus, NetworkItem

from . import bridge_protocol as protocol, game_copy
from .bridge_connection import BridgeConnection
from .data import BASE_ID, LOCATIONS
from .items import GAME

SHOWN_STORE = "swd2_items_shown"  # persistent storage: "<seed name>:<slot>" -> how many items the game has shown
HIDDEN_NAME = "Archipelago Item"  # an item on offer, when the seed hides shop items

# The locations whose item the game names before you get it. Shop slots and the Cartographer's rewards are hidden
# when the seed hides shop items, and podiums name theirs in the banner once taken
OFFER_TYPES = ("workbench", "carson", "clifford", "cartographer")
NAMED_LOCATIONS = {
    BASE_ID + location.id: location.type
    for location in LOCATIONS
    if location.type in OFFER_TYPES + ("podium",)
}


class SWD2CommandProcessor(ClientCommandProcessor):
    ctx: "SWD2Context"

    @mark_raw
    def _cmd_auto_patch(self, game_folder: str = "") -> bool:
        """Make the patched copy of the game in Archipelago's folder from the Steam or GOG install, which is found by itself or given as the game folder."""
        Utils.async_start(self.ctx.auto_patch(game_folder.strip().strip('"')), name="auto patch")
        return True

    def _cmd_launch(self) -> bool:
        """Start the patched copy of the game."""
        problem = game_copy.copy_problem()
        if problem:
            self.output(f"Can't start the game: {problem}. Run /auto_patch first.")
            return False

        if sys.platform != "win32":
            self.output(f"Start the copy in {game_copy.copy_dir()} from Steam or Wine (README)")
            return False

        game_copy.launch()
        return True

    def _cmd_deathlink(self) -> bool:
        """Turn DeathLink on or off until the client closes."""
        if self.ctx.slot_data is None:
            self.output("Connect to your room first.")
            return False

        death_link = "DeathLink" not in self.ctx.tags
        Utils.async_start(self.ctx.update_death_link(death_link), name="DeathLink")
        self.output(f"DeathLink is {'on' if death_link else 'off'}.")
        return True


class SWD2Context(CommonContext):
    game = GAME
    items_handling = 0b111  # every item comes through the bridge: other worlds, your own and the starting inventory
    want_slot_data = True
    command_processor = SWD2CommandProcessor

    def __init__(self, server_address: str | None, password: str | None):
        super().__init__(server_address, password)
        self.bridge = BridgeConnection(self.on_bridge_message, self.on_bridge_closed)
        self.game_ready = False  # the bridge said hello and runs in a supported game
        self.slot_data: dict | None = None
        self.shown = 0
        self.save_report: dict | None = None  # the bridge's last "save" report
        self.bridge_busy = False  # the bridge said another client is connected
        self.death_link_slot: str | None = None  # the slot whose YAML setting DeathLink took

    def make_gui(self):
        ui = super().make_gui()
        ui.base_title = "SteamWorld Dig 2 Client"
        return ui

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)

        await self.get_username()
        await self.send_connect()

    def reset_server_state(self):
        # The slot's data goes with the server connection: without it nothing is sent to the bridge for a slot
        super().reset_server_state()
        self.slot_data = None

    @property
    def seed_id(self) -> int:
        return protocol.seed_id(self.server_seed_name, self.slot)

    def save_is_ours(self) -> bool:
        """Whether the loaded save belongs to this slot. Until then the bridge may still report a save of the slot it
        was connected to before."""
        report = self.save_report
        if self.slot is None or report is None:
            return False

        return report["state"] == "bound" and report["seed"] == self.seed_id

    @property
    def shown_key(self) -> str:
        return f"{self.server_seed_name}:{self.slot}"

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            self.slot_data = args["slot_data"]
            self.shown = Utils.persistent_load().get(SHOWN_STORE, {}).get(self.shown_key, 0)
            Utils.async_start(self.scout_items_on_offer(), name="scout")

            # Once per slot, so a /deathlink lasts through reconnects. A seed from 0.1.0 has no such option
            if self.death_link_slot != self.shown_key:
                self.death_link_slot = self.shown_key
                death_link = self.slot_data.get("death_link", False)
                Utils.async_start(self.update_death_link(death_link), name="DeathLink")

            if self.game_ready:
                self.send_slot()

        elif cmd == "ReceivedItems":
            # Wait while a resync is pending: it sends every item again
            start = args["index"]
            if self.game_ready and start + len(args["items"]) == len(self.items_received):
                self.send_items(start)

        elif cmd == "LocationInfo":
            if self.game_ready:
                self.bridge.send(protocol.texts_message(self.names_on_offer()))

    def on_print_json(self, args: dict):
        """Shows a banner in game for each item you find for another player. Your own come as received items."""
        super().on_print_json(args)

        # After the goal the server releases your remaining items, which you didn't find
        if args.get("type") != "ItemSend" or self.slot is None or self.finished_game:
            return

        item: NetworkItem = args["item"]
        receiver = args["receiving"]
        if item.player != self.slot or receiver == self.slot:
            return

        header, text = protocol.item_banner(
            self.player_names[self.slot],
            self.item_names.lookup_in_slot(item.item, receiver),
            self.player_names[receiver],
            self.location_names.lookup_in_slot(item.location, self.slot),
        )
        self.bridge.send(protocol.banner_message(header, text))

    def on_deathlink(self, data: dict):
        super().on_deathlink(data)

        if self.game_ready:
            self.bridge.send(protocol.kill_message())

    async def scout_items_on_offer(self):
        show = self.slot_data["options"]["show_shop_items"]
        scouts = [
            location
            for location, kind in NAMED_LOCATIONS.items()
            if location in self.server_locations and (show or kind not in OFFER_TYPES)
        ]
        await self.send_msgs([{"cmd": "LocationScouts", "locations": scouts, "create_as_hint": 0}])

    def names_on_offer(self) -> dict[int, str]:
        """What the game calls the item at each named location."""
        show = self.slot_data["options"]["show_shop_items"]
        names = {}

        for location, kind in NAMED_LOCATIONS.items():
            if not show and kind in OFFER_TYPES:
                names[location] = HIDDEN_NAME
            elif location in self.locations_info:
                item = self.locations_info[location]
                name = self.item_names.lookup_in_slot(item.item, item.player)
                names[location] = name if item.player == self.slot else f"{self.player_names[item.player]}'s {name}"

        return names

    def send_slot(self):
        """Sends the bridge everything it needs for this slot, after connecting to either side."""
        shop_prices = {int(location): price for location, price in self.slot_data["shop_prices"].items()}

        self.bridge.send(protocol.connect_message(self.seed_id))
        self.bridge.send(protocol.prices_message(shop_prices))
        self.bridge.send(protocol.texts_message(self.names_on_offer()))
        self.send_items(0)

        if self.save_report:
            self.judge_save()

    def send_items(self, start: int):
        money = {int(item): dollars for item, dollars in self.slot_data["money_bundles"].items()}
        grants = protocol.grants([item.item for item in self.items_received], money)
        banners = [
            protocol.item_banner(
                self.player_names[item.player],
                self.item_names.lookup_in_game(item.item),
                self.player_names[self.slot],
                self.location_names.lookup_in_slot(item.location, item.player),
            )
            for item in self.items_received
        ]
        self.bridge.send(protocol.items_message(grants, banners, start, self.shown))

    async def on_bridge_message(self, message: dict):
        kind = message.get("type")

        if kind == "hello":
            self.on_hello(message)
        elif kind == "save":
            self.save_report = message
            if self.slot_data:
                self.judge_save()
        elif kind == "checks":
            await self.on_checks(message)
        elif kind == "busy":
            self.on_busy()
        elif kind == "death" and "DeathLink" in self.tags:
            await self.send_death()

    def on_hello(self, message: dict):
        self.bridge_busy = False

        if message.get("protocol") != protocol.PROTOCOL_VERSION:
            logger.error(
                f"The game's bridge speaks protocol {message.get('protocol')} and this client "
                f"{protocol.PROTOCOL_VERSION}: run /auto_patch to install the bridge that matches this client."
            )
        elif not message.get("game_ok"):
            logger.error(f"The bridge can't run in this game: {message.get('error')}")
        else:
            logger.info("Connected to the game.")
            self.game_ready = True
            if self.slot_data:
                self.send_slot()

    def on_busy(self):
        if not self.bridge_busy:
            logger.error("Another SteamWorld Dig 2 Client is connected to the game. Close it to play this slot here.")

        self.bridge_busy = True

    def on_bridge_closed(self):
        if self.game_ready:
            logger.info("The game closed the connection.")

        self.game_ready = False
        self.save_report = None

    def tell(self, header: str, text: str):
        logger.info(f"{header} {text}")
        self.bridge.send(protocol.banner_message(header, text))

    def judge_save(self):
        """Says so when the loaded save can't play this slot, and raises the "shown" count as the save's items grow."""
        report = self.save_report

        if report["state"] == "vanilla":
            self.tell("Not an Archipelago save.", "Start a New Game to play your slot.")
        elif report["state"] == "bound" and report["seed"] != self.seed_id:
            self.tell("This save belongs to another seed or slot.", "Load this slot's save or start a New Game.")
        elif report["state"] == "bound" and report["items"] > self.shown:
            self.shown = report["items"]
            Utils.persistent_store(SHOWN_STORE, self.shown_key, self.shown)

    async def on_checks(self, report: dict):
        if not self.save_is_ours():
            return

        # Only the locations the slot has: El Machino's teleporter, for one, isn't a location
        found = protocol.found_locations(report) & self.server_locations

        # Kept so a reconnect sends them again
        self.locations_checked |= found
        await self.check_locations(found)

        if protocol.goal_reached(report) and not self.finished_game:
            self.finished_game = True
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])

    async def auto_patch(self, game_folder: str):
        source = pathlib.Path(game_folder) if game_folder else game_copy.find_install()
        if source is None:
            logger.info("No Steam or GOG install of SteamWorld Dig 2 was found: give its folder, /auto_patch <folder>.")
            if sys.platform != "win32":
                logger.info("On Linux it must be the Windows version (README)")
            return

        # The copy runs in a thread, so its messages go back to the client's loop
        loop = asyncio.get_running_loop()

        def log(text):
            loop.call_soon_threadsafe(logger.info, text)

        logger.info("Patching, this takes a minute...")
        try:
            target = await asyncio.to_thread(game_copy.make_patched_copy, source, log)
        except (OSError, ValueError) as error:
            logger.error(f"Patching failed: {error}")
            return
        except Exception:
            logger.exception("Patching failed")
            return

        logger.info(f"The patched game is ready in {target}. Start it with /launch.")

    def report_patched_copy(self):
        problem = game_copy.copy_problem()
        if problem:
            logger.info(f"Before playing: {problem}. Run /auto_patch.")


async def run(args):
    ctx = SWD2Context(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    bridge_task = asyncio.create_task(ctx.bridge.run(ctx.exit_event), name="bridge")

    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()
    ctx.report_patched_copy()

    await ctx.exit_event.wait()
    bridge_task.cancel()
    await ctx.shutdown()


def main(*args: str):
    import colorama

    Utils.init_logging("SWD2Client", exception_logger="Client")

    parser = get_base_parser(description="SteamWorld Dig 2 Client: connects the game to Archipelago.")
    parser.add_argument("--name", default=None, help="Slot name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    args = handle_url_arg(parser.parse_args(args), parser=parser)

    colorama.just_fix_windows_console()
    asyncio.run(run(args))
    colorama.deinit()
