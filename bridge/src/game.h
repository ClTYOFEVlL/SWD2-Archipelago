// Where Dig2.exe's functions and data are (in the Steam build only), and wrappers that call them the way the game
// does. The game is 32-bit MSVC 2010, so its strings are read and built by hand.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace game {

// The functions the bridge hooks or calls, as offsets from the module base (Windows moves the exe at each start)
namespace rva {
const uintptr_t SimulatorsUpdate = 0x25C830;   // runs once a frame, also while paused: the bridge's tick
const uintptr_t SetUpgradeNode = 0x253A60;     // the SetUpgrade script node
const uintptr_t SetUpgradeTier = 0x235760;     // what scripts and the workbench use, which rebuilds the player's tools
const uintptr_t PlayerUpgradesSet = 0x26CD80;  // the table write underneath it, without the rebuild
const uintptr_t GiveBlueprint = 0x2371F0;
const uintptr_t AddMoney = 0x236CB0;
const uintptr_t AddCogs = 0x237150;
const uintptr_t FindCollectible = 0x229B40;
const uintptr_t GiveCollectible = 0x228680;    // gives an artifact the way a pickup does
const uintptr_t BannerShow = 0x2749F0;
const uintptr_t Intern = 0x38D160;
const uintptr_t FindPlayerComponent = 0x21BD80;
const uintptr_t PriceListCount = 0x269E40;     // how many items of a price list (Carson, Clifford) were bought
const uintptr_t Localize = 0x30BE00;           // the text lookup: text id -> text
const uintptr_t ToolsScreenMode = 0x168430;    // the workbench screen switches between upgrades and cog mods
const uintptr_t ToolsScreenRefresh = 0x16C680;
}  // namespace rva

// Checks the exe and finds it in memory. Returns false, and why, unless this is the supported Steam build
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
