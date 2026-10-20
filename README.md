# SteamWorld Dig 2 Archipelago

An [Archipelago](https://archipelago.gg) implementation for SteamWorld Dig 2

- The locations are the cog containers, artifacts, upgrade podiums, the Yonker brothers' blueprints, the workbench's upgrade tiers, Trader Carson's and Clifford's wares, the Cartographer's rewards and, optionally, the teleporters and the Trials.
- The items are the tool upgrades (Progressive Pickaxe, Backpack, Lamp, Armor, Water Tank, Pressure Bomb, Jackhammer and Jet Engine, the Hook Shot and the Sprint Hydraulics), the cog mod blueprints, the 43 artifacts, Upgrade Cogs and money bundles. Each Progressive item is the next tier of its tool.
- The goal is to defeat Rosie.

## Setup

1. Download the latest `swd2.apworld` from the releases
2. Double click the apworld to automatically install it (or manually move it to `custom_worlds`)
3. In the Archipelago Launcher, open "SteamWorld Dig 2 Client"
4. Type `/auto_patch` to make the patched copy. It finds the Steam or GOG install by itself, or give it the game's folder: `/auto_patch <directory>`. Run it again whenever you update the apworld
5. Type `/launch` to start the patched copy, connect to your room, then start a New Game

**Saves:** The patched copy shares its save slots with the normal game. Never open an Archipelago save in the normal game and never open a normal save in the Archipelago copy. The unpatched game removes the save's Archipelago data, and in the patched copy a normal save gets nothing from what it finds. If it happens, close the game and restore `savegame_00N.dat.backup` (in `Documents\My Games\SteamWorld Dig 2\<a number>` for Steam, `Documents\My Games\SteamWorld Dig 2` for GOG) before playing on. Play each slot on a save of its own.

### Linux

> Linux support is untested. If you do try it, please open an issue with how it went and attach `swd2ap_bridge.log` from the patched copy's folder

1. Get the Windows version
    - **Steam**: In the game's Properties -> Compatibility, check `Force the use of a specific Steam Play compatibility tool`
    - **GOG**: Install the Windows version
2. Do steps 1-4 of the Setup
3. In Steam, add the patched copy's `Dig2.exe` as a Non-Steam game. In its Properties:
    - Compatibility: check `Force the use of a specific Steam Play compatibility tool`
    - Launch Options: `WINEDLLOVERRIDES="version=n,b" %command%`
4. Start it from Steam

## Troubleshooting

- You get the "version.dll is missing or can't be read" error
    - Make sure that your anti-virus did not delete any files. Add your `Archipelago` install to the exclusions and restore any affected items
    - **Windows Defender**: 
        - Virus & threat protection settings -> Manage settings -> Exclusions -> Add your `Archipelago` install
        - Virus & threat protection -> Protection history -> Restore any deleted files

## Credits

- Thanks to [SWD2Randomizer](https://github.com/clementgallet/SWD2Randomizer) by clementgallet. Its logic was used as a reference and some game fixes follow it
