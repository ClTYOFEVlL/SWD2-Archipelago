// Where Dig2.exe's functions and data are and wrappers that call them the way the game
// does. The game is 32-bit MSVC 2010, so its strings are read and built by hand.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace game {

// What differs between the builds: where the functions and data are, as offsets from the module base (Windows moves
// the exe at each start), and the fields of the tools screen, the one object whose layout changed
struct Build {
    const char* name;
    const char* sha256;

    // The functions the bridge hooks or calls
    uintptr_t SimulatorsUpdate;  // runs once a frame, also while paused: the bridge's tick
    uintptr_t SetUpgradeNode;  // the SetUpgrade script node
    uintptr_t SetUpgradeTier;  // what scripts and the workbench use, which rebuilds the player's tools
    uintptr_t PlayerUpgradesSet;  // the table write underneath it, without the rebuild
    uintptr_t GiveBlueprint;
    uintptr_t AddMoney;
    uintptr_t AddCogs;
    uintptr_t FindCollectible;
    uintptr_t GiveCollectible;  // gives an artifact the way a pickup does
    uintptr_t BannerShow;
    uintptr_t Intern;
    uintptr_t FindPlayerComponent;
    uintptr_t PriceListCount;  // how many items of a price list (Carson, Clifford) were bought
    uintptr_t Localize;  // the text lookup: text id -> text
    uintptr_t ToolsScreenMode;  // the workbench screen switches between upgrades and cog mods
    uintptr_t ToolsScreenRefresh;

    // Data in the exe
    uintptr_t DeathThreshold;  // a float, the player is dead below it
    uintptr_t UpgradeDefs;  // a vector of 8-byte entries, the definition pointer first
    uintptr_t PriceListDefs;  // the same, for price lists
    uintptr_t EntityTableIndex;
    uintptr_t EntityTableVtable;

    // The tools screen's fields
    uintptr_t ScreenMode;  // 0 upgrades, 1 cog mods
    uintptr_t ScreenCanBuy;  // true only at the workbench itself
    uintptr_t ScreenRows;  // its rows, begin then end, 8-byte shared pointers, the row first
    uintptr_t RowDefinition;  // the upgrade definition a row shows
};

// The running build once Init has found it
extern const Build* g_build;

// Checks the exe and finds it in memory. Returns false, and why, unless this is the Steam or the GOG build
bool Init(std::string& why);

// The module base + offset
uintptr_t At(uintptr_t offset);

// The objects of one frame. A level load rebuilds all but the profile (the save in memory), so never keep them
struct Frame {
    uintptr_t game = 0;
    uintptr_t profile = 0;
    uintptr_t playerSim = 0;
    uintptr_t pickupSim = 0;

    bool Valid() const;
};
Frame FrameOf(uintptr_t simulators);

// The engine's id for a string
const char* Intern(const char* s);

// False while the player is dead, and while there's no player (during level loads)
bool PlayerAlive(const Frame& frame);

// Stands still while the game is paused or its window unfocused
double GameTime(uintptr_t profile);

// The profile's upgrade table: every upgrade above tier 0, hidden flags included
struct Upgrade {
    char name[64];
    int tier;
};
void ReadUpgrades(uintptr_t profile, std::vector<Upgrade>& out);
int TierIn(const std::vector<Upgrade>& table, const char* id);  // 0 if it isn't there

// Changes to the profile. Only on the game thread, and only at the start of a frame (hooks.cpp says why)
void SetUpgradeTier(const Frame& frame, const char* id, int tier, bool hideNew);  // a tool: it takes effect at once
void SetFlag(uintptr_t profile, const char* id, int tier);  // a hidden flag: the table only, no rebuild of the tools
void GiveBlueprint(const Frame& frame, const char* id, bool banner);
bool GiveArtifact(const Frame& frame, const char* collectible);  // false if the player has no position yet
void AddMoney(const Frame& frame, int amount, bool silent);
void AddCogs(const Frame& frame, int amount, bool silent);
void ShowBanner(const Frame& frame, const char* header, const char* text, const char* icon);

// Reading the profile
void ReadTeleporters(uintptr_t profile, std::vector<std::string>& out);  // the unlocked ones, by name
int PriceListCount(uintptr_t profile, const char* list);                 // `list` is an interned id
int CartographerPaid(uintptr_t profile);  // the artifact threshold of the last reward he paid, 0 for none yet

// The definitions, loaded once at startup. Prices written here last until the game closes
uintptr_t FindUpgradeDef(const char* id);
const char* UpgradeIcon(const char* id, int tier);  // the icon path of an upgrade's tier, or nullptr
const char* ArtifactIcon(const char* collectible);
bool SetUpgradePrice(const char* id, int tier, int price);
bool SetPriceListPrice(const char* list, int index, int price);

}  // namespace game
