#include "game.h"

#include <windows.h>
#include <cstring>
#include <fstream>
#include <iterator>

#include "log.h"
#include "memory.h"
#include "picosha2/picosha2.h"

namespace game {

const Build* g_build = nullptr;

namespace {

uintptr_t g_base = 0;

// Steam build 2103185 of Dig2.exe (2017-09-08)
const Build kSteam = {
    .name = "Steam",
    .sha256 = "4583a9b1ec614d23ea3503c97a89c0d6e36d88d3292203f409adc1f529d0b5e5",

    .SimulatorsUpdate = 0x25C830,
    .SetUpgradeNode = 0x253A60,
    .SetUpgradeTier = 0x235760,
    .PlayerUpgradesSet = 0x26CD80,
    .GiveBlueprint = 0x2371F0,
    .AddMoney = 0x236CB0,
    .AddCogs = 0x237150,
    .FindCollectible = 0x229B40,
    .GiveCollectible = 0x228680,
    .BannerShow = 0x2749F0,
    .Intern = 0x38D160,
    .FindPlayerComponent = 0x21BD80,
    .PriceListCount = 0x269E40,
    .Localize = 0x30BE00,
    .ToolsScreenMode = 0x168430,
    .ToolsScreenRefresh = 0x16C680,

    .DeathThreshold = 0x537268,
    .UpgradeDefs = 0x622948,
    .PriceListDefs = 0x622150,
    .EntityTableIndex = 0x619860,
    .EntityTableVtable = 0x508384,

    .ScreenMode = 0x140,
    .ScreenCanBuy = 0x144,
    .ScreenRows = 0x154,
    .RowDefinition = 0x29C,
};

// GOG's 1.1 (2017-09-18) - the same code at other addresses
const Build kGog = {
    .name = "GOG",
    .sha256 = "0814849a24fcbddebb63172372268a58a36aaf29d5489b19714b573b9cfcc7b9",

    .SimulatorsUpdate = 0x25C250,
    .SetUpgradeNode = 0x2534D0,
    .SetUpgradeTier = 0x235210,
    .PlayerUpgradesSet = 0x26C710,
    .GiveBlueprint = 0x236CA0,
    .AddMoney = 0x236760,
    .AddCogs = 0x236C00,
    .FindCollectible = 0x229750,
    .GiveCollectible = 0x228220,
    .BannerShow = 0x274570,
    .Intern = 0x38F220,
    .FindPlayerComponent = 0x21BAA0,
    .PriceListCount = 0x2698C0,
    .Localize = 0x30D290,
    .ToolsScreenMode = 0x168230,
    .ToolsScreenRefresh = 0x16C480,

    .DeathThreshold = 0x534DF8,
    .UpgradeDefs = 0x61CFB0,
    .PriceListDefs = 0x61C7B8,
    .EntityTableIndex = 0x613EE0,
    .EntityTableVtable = 0x506394,

    .ScreenMode = 0x148,
    .ScreenCanBuy = 0x14C,
    .ScreenRows = 0x15C,
    .RowDefinition = 0x2A4,
};

const Build* const kBuilds[] = {&kSteam, &kGog};

// The Simulators object that Simulators::Update receives
const uintptr_t kSimulatorsGame = 0xC;  // points at an object with the Game at +4
const uintptr_t kSimulatorsPlayer = 0x20;  // the PlayerSimulator
const uintptr_t kSimulatorsPickup = 0x6C;  // the PickupSimulator

// The Game object
const uintptr_t kGameEntities = 0x36C;  // the entity system
const uintptr_t kGamePlayerId = 0x260;  // the player's entity id
const uintptr_t kGameProfile = 0x3CC;  // the profile, the save in memory
const uintptr_t kGameBanners = 0x40C;  // the BannerUI

const uintptr_t kPlayerSimGame = 0x14;  // the PlayerSimulator points back at the Game

// The profile
const uintptr_t kProfileGameTime = 0x10;  // a double
const uintptr_t kProfileTeleporters = 0xB8;  // the unlocked ones: a vector of game strings, begin then end
const uintptr_t kProfileUpgrades = 0x168;  // the upgrade table: buckets, then the bucket count, then the size
const uintptr_t kProfileCartographerPaid = 0x1E0;

// Definitions, loaded at startup
const uintptr_t kDefinitionId = 4;  // a definition's id string
const uintptr_t kUpgradeDefTiers = 0x24;  // an upgrade definition's tiers, begin then end
const uintptr_t kTierSize = 0x78;  // a tier's MoneyCost is at +0
const uintptr_t kTierIcon = 0x14;
const uintptr_t kCollectibleIcon = 0x18;
const uintptr_t kPriceListPrices = 0xC;  // a price list's prices, a vector of ints, begin then end
const uintptr_t kGameStringSize = 0x1C;  // the game's std::string (memory.h)

// The entity table, a hash map: each node's link to the next one is at +0x70, its entity at +8, and an entity's id
// at +4 and position at +0x30
const uintptr_t kEntityTableStride = 0x4C;
const uintptr_t kNodeLink = 0x70;
const uintptr_t kNodeEntity = 8;
const uintptr_t kEntityId = 4;
const uintptr_t kEntityPosition = 0x30;

const uintptr_t kPlayerHealth = 0x14;  // the player component's Health
const uintptr_t kHealthPoints = 0x10;  // a float

// Each function's first bytes, the same in both builds, up to its first absolute address (those get relocated)
struct Prologue {
    uintptr_t offset;
    const char* name;
    unsigned char bytes[20];
    size_t size;
};

bool ProloguesMatch(const Build& build, std::string& why)
{
    const Prologue prologues[] = {
        {build.SimulatorsUpdate, "Simulators::Update", {0x55, 0x8B, 0xEC, 0x53, 0x8B, 0x1D}, 6},
        {build.SetUpgradeNode, "SetUpgrade node", {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x6A, 0xFF, 0x68}, 9},
        {build.SetUpgradeTier, "SetUpgradeTier", {0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68}, 6},
        {build.PlayerUpgradesSet, "PlayerUpgrades::Set", {0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68}, 6},
        {build.GiveBlueprint, "GiveBlueprint",
         {0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0x53, 0x8B, 0x5D, 0x08, 0x56, 0x8B, 0x73, 0x14}, 14},
        {build.AddMoney, "AddMoney", {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x6A, 0xFF, 0x68}, 9},
        {build.AddCogs, "AddCogs",
         {0x55, 0x8B, 0xEC, 0x8B, 0x47, 0x14, 0x8B, 0x88, 0x60, 0x02, 0x00, 0x00, 0x53, 0x56, 0x51}, 15},
        {build.FindCollectible, "FindCollectible", {0x55, 0x8B, 0xEC, 0x51, 0x83, 0x3D}, 6},
        {build.GiveCollectible, "GiveCollectible", {0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68}, 6},
        {build.BannerShow, "BannerUI::Show", {0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68}, 6},
        {build.Intern, "Intern", {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x6A, 0xFF, 0x68}, 9},
        {build.FindPlayerComponent, "FindPlayerComponent",
         {0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08, 0x56, 0x8B, 0x75, 0x08, 0x57, 0x8B, 0xF8, 0x8B, 0x47, 0x04}, 16},
        {build.PriceListCount, "PriceListCount",
         {0x55, 0x8B, 0xEC, 0x51, 0x56, 0x8B, 0xF0, 0x83, 0xBE, 0x1C, 0x01, 0x00, 0x00}, 13},
        {build.Localize, "Localize", {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x6A, 0xFF, 0x68}, 9},
        {build.ToolsScreenMode, "ToolsScreen mode",
         {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x0C, 0x8B, 0x45, 0x08, 0x53, 0x56, 0x8B, 0xF1}, 16},
        {build.ToolsScreenRefresh, "ToolsScreen refresh", {0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x6A, 0xFF, 0x68}, 9},
    };

    for (const Prologue& prologue : prologues) {
        if (memcmp(reinterpret_cast<const void*>(g_base + prologue.offset), prologue.bytes, prologue.size) != 0) {
            why = std::string("unexpected code at ") + prologue.name;
            return false;
        }
    }

    return true;
}

// The game's calling conventions. __thiscall functions are called through a pointer of that type
typedef const char*(__cdecl* InternFn)(const char* s);
typedef void(__stdcall* SetUpgradeTierFn)(uintptr_t playerSim, const char* id, int tier, int hideNew);
typedef void(__stdcall* PlayerUpgradesSetFn)(uintptr_t upgrades, const char* id, int tier, int hide);
typedef void(__stdcall* GiveBlueprintFn)(uintptr_t playerSim, const char* id, int banner);
typedef void(__thiscall* AddMoneyFn)(uintptr_t playerSim, int amount, unsigned flags);
typedef uintptr_t(__fastcall* FindCollectibleFn)(const char** name);
typedef void(__stdcall* GiveCollectibleFn)(uintptr_t pickupSim, uintptr_t definition, const float* pos);
typedef void(__stdcall* BannerShowFn)(uintptr_t bannerUI, const char* key, const char* headerId, const char* headerArg,
                                      const char* textId, const char* textArg, const char* icon);

// A game function at an offset, as a pointer of the right type
template <typename T>
T Fn(uintptr_t offset)
{
    return reinterpret_cast<T>(g_base + offset);
}

// The running Dig2.exe's SHA-256 in hex, or "" if the file can't be read
std::string ExeSha256()
{
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(nullptr, path, MAX_PATH);

    std::ifstream file(path, std::ios::binary);
    if (!file) return "";

    std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return picosha2::hash256_hex_string(bytes);
}

// Finds a definition by id in a definition table
uintptr_t FindDef(uintptr_t table, const char* id)
{
    uintptr_t begin = ReadU32(g_base + table);
    uintptr_t end = ReadU32(g_base + table + 4);

    for (uintptr_t it = begin; it < end && it < begin + 8 * 1024; it += 8) {
        char name[64];
        uintptr_t definition = ReadU32(it);
        if (ReadCStr(ReadU32(definition + kDefinitionId), name, sizeof(name)) && !strcmp(name, id))
            return definition;
    }

    return 0;
}

// One tier of an upgrade definition, or 0
uintptr_t TierOf(const char* id, int tier)
{
    uintptr_t definition = FindUpgradeDef(id);
    if (!definition || tier < 1) return 0;

    uintptr_t at = ReadU32(definition + kUpgradeDefTiers) + kTierSize * (tier - 1);
    return at < ReadU32(definition + kUpgradeDefTiers + 4) ? at : 0;
}

uintptr_t FindCollectibleDef(const char* name)
{
    const char* id = Intern(name);
    return Fn<FindCollectibleFn>(g_build->FindCollectible)(&id);
}

// The player's position (the middle of the feet), found in the entity table. Its nodes are chained in one list that
// starts at bucket[count]
bool PlayerPosition(const Frame& frame, float pos[2])
{
    uintptr_t entities = frame.game + kGameEntities;
    uintptr_t table = ReadU32(ReadU32(entities) + ReadU32(g_base + g_build->EntityTableIndex) * kEntityTableStride);
    if (ReadU32(table) != g_base + g_build->EntityTableVtable) return false;

    uint32_t player = ReadU32(frame.game + kGamePlayerId);
    uintptr_t buckets = ReadU32(table + 4);
    uintptr_t count = ReadU32(table + 8);
    uintptr_t link = buckets ? ReadU32(buckets + 4 * count) : 0;

    for (int guard = 0; link && guard < 100000; ++guard, link = ReadU32(link)) {
        uintptr_t entity = link - kNodeLink + kNodeEntity;
        if (ReadU32(entity + kEntityId) == player) {
            pos[0] = ReadF32(entity + kEntityPosition);
            pos[1] = ReadF32(entity + kEntityPosition + 4);
            return true;
        }
    }

    return false;
}

}  // namespace

bool Init(std::string& why)
{
    g_base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));

    std::string hash = ExeSha256();
    if (hash.empty()) {
        why = "could not read Dig2.exe";
        return false;
    }
    for (const Build* build : kBuilds)
        if (hash == build->sha256)
            g_build = build;

    if (!g_build) {
        why = "unsupported Dig2.exe (SHA-256 " + hash + "): only the Steam and GOG builds are supported";
        return false;
    }

    if (!ProloguesMatch(*g_build, why)) return false;

    Log("Dig2.exe is the %s build; base %08X", g_build->name, static_cast<unsigned>(g_base));
    return true;
}

uintptr_t At(uintptr_t offset)
{
    return g_base + offset;
}

Frame FrameOf(uintptr_t simulators)
{
    Frame frame;
    frame.game = ReadU32(ReadU32(simulators + kSimulatorsGame) + 4);
    frame.playerSim = ReadU32(simulators + kSimulatorsPlayer);
    frame.pickupSim = ReadU32(simulators + kSimulatorsPickup);
    frame.profile = frame.game ? ReadU32(frame.game + kGameProfile) : 0;
    return frame;
}

bool Frame::Valid() const
{
    return game && profile && playerSim && pickupSim && ReadU32(playerSim + kPlayerSimGame) == game;
}

const char* Intern(const char* s)
{
    return Fn<InternFn>(g_build->Intern)(s);
}

// FindPlayerComponent takes the entity system in eax and the entity id on the stack, and pops it (ret 4). It returns
// 0 when the player doesn't exist or is being destroyed
bool PlayerAlive(const Frame& frame)
{
    void* fn = reinterpret_cast<void*>(g_base + g_build->FindPlayerComponent);
    uint32_t entities = frame.game + kGameEntities;
    uint32_t id = ReadU32(frame.game + kGamePlayerId);
    uint32_t component = 0;

    __asm {
        push id
        mov eax, entities
        call fn
        mov component, eax
    }

    if (!component) return false;

    return ReadF32(ReadU32(component + kPlayerHealth) + kHealthPoints) > ReadF32(g_base + g_build->DeathThreshold);
}

double GameTime(uintptr_t profile)
{
    return ReadF64(profile + kProfileGameTime);
}

// The upgrade table is a hash map whose nodes form one list, starting at bucket[count]. Each link points at the next
// one, with the node's name (an interned char*) 8 bytes before the link and its tier 4 bytes before. Tier 0 removes
// an entry
void ReadUpgrades(uintptr_t profile, std::vector<Upgrade>& out)
{
    out.clear();

    uintptr_t buckets = ReadU32(profile + kProfileUpgrades);
    uintptr_t count = ReadU32(profile + kProfileUpgrades + 4);
    if (!buckets || count > 1 << 16) return;

    uintptr_t link = ReadU32(buckets + 4 * count);
    for (int guard = 0; link && guard < 4096; ++guard, link = ReadU32(link)) {
        Upgrade upgrade;
        if (ReadCStr(ReadU32(link - 8), upgrade.name, sizeof(upgrade.name)) && upgrade.name[0]) {
            upgrade.tier = static_cast<int>(ReadU32(link - 4));
            out.push_back(upgrade);
        }
    }

    static bool warned = false;
    uint32_t size = ReadU32(profile + kProfileUpgrades + 8);
    if (!warned && out.size() != size) {
        warned = true;
        Log("warning: read %u upgrades, the table says %u", static_cast<unsigned>(out.size()), size);
    }
}

int TierIn(const std::vector<Upgrade>& table, const char* id)
{
    for (const Upgrade& upgrade : table)
        if (!strcmp(upgrade.name, id))
            return upgrade.tier;

    return 0;
}

// What scripts and the workbench call. It rebuilds the player's tools, does nothing while the player is dead, and
// shows no banner
void SetUpgradeTier(const Frame& frame, const char* id, int tier, bool hideNew)
{
    Fn<SetUpgradeTierFn>(g_build->SetUpgradeTier)(frame.playerSim, Intern(id), tier, hideNew ? 1 : 0);
}

// The table write itself, PlayerUpgrades::Set. It refuses an id that isn't defined or a tier past the upgrade's last.
// It doesn't rebuild the tools, so it's safe for flags at any point of a frame
void SetFlag(uintptr_t profile, const char* id, int tier)
{
    Fn<PlayerUpgradesSetFn>(g_build->PlayerUpgradesSet)(profile + kProfileUpgrades, Intern(id), tier, 1);
}

// Unlocks a blueprint (a cog mod), with or without the game's banner
void GiveBlueprint(const Frame& frame, const char* id, bool banner)
{
    Fn<GiveBlueprintFn>(g_build->GiveBlueprint)(frame.playerSim, Intern(id), banner ? 1 : 0);
}

// GiveCollectible adds the artifact unless it's owned already, with its "+1" text at a position (here the player's)
// and the game's artifact banner
bool GiveArtifact(const Frame& frame, const char* collectible)
{
    uintptr_t definition = FindCollectibleDef(collectible);
    if (!definition) {
        Log("no artifact named '%s': nothing given", collectible);
        return true;
    }

    float pos[2];
    if (!PlayerPosition(frame, pos)) return false;

    Fn<GiveCollectibleFn>(g_build->GiveCollectible)(frame.pickupSim, definition, pos);
    return true;
}

// Flags 3 is what the script node passes (the HUD counter and a "+$" text), and 0 shows nothing. Does nothing while
// the player is dead
void AddMoney(const Frame& frame, int amount, bool silent)
{
    Fn<AddMoneyFn>(g_build->AddMoney)(frame.playerSim, amount, silent ? 0 : 3);
}

// AddCogs takes the PlayerSimulator in edi and (cogs, silent) on the stack, and pops them (ret 8). It shows the HUD's
// cog counter unless silent
void AddCogs(const Frame& frame, int amount, bool silent)
{
    void* fn = reinterpret_cast<void*>(g_base + g_build->AddCogs);
    uint32_t sim = frame.playerSim;
    uint32_t quiet = silent ? 1 : 0;

    __asm {
        push edi
        mov edi, sim
        push quiet
        push amount
        call fn
        pop edi
    }
}

// banner_blueprint is the white two-line banner with an icon, and menu_map_no_secrets is the text "%1%" in every
// language, so the two arguments show as they are. Banners with the same key wait their turn, 4 seconds each
void ShowBanner(const Frame& frame, const char* header, const char* text, const char* icon)
{
    static const char* key = Intern("banner_blueprint");
    static const char* plain = Intern("menu_map_no_secrets");
    Fn<BannerShowFn>(g_build->BannerShow)(ReadU32(frame.game + kGameBanners), key, plain, header, plain, text, icon);
}

void ReadTeleporters(uintptr_t profile, std::vector<std::string>& out)
{
    out.clear();

    uintptr_t begin = ReadU32(profile + kProfileTeleporters);
    uintptr_t end = ReadU32(profile + kProfileTeleporters + 4);

    for (uintptr_t at = begin; at < end && at < begin + kGameStringSize * 256; at += kGameStringSize) {
        char name[64];
        if (ReadGameString(at, name, sizeof(name)) && name[0])
            out.push_back(name);
    }
}

// PriceListCount takes the profile in eax and the list id on the stack, and pops it (ret 4)
int PriceListCount(uintptr_t profile, const char* list)
{
    void* fn = reinterpret_cast<void*>(g_base + g_build->PriceListCount);
    uint32_t p = profile;
    int count = 0;

    __asm {
        push list
        mov eax, p
        call fn
        mov count, eax
    }

    return count;
}

int CartographerPaid(uintptr_t profile)
{
    return static_cast<int>(ReadU32(profile + kProfileCartographerPaid));
}

uintptr_t FindUpgradeDef(const char* id)
{
    return FindDef(g_build->UpgradeDefs, id);
}

const char* UpgradeIcon(const char* id, int tier)
{
    uintptr_t at = TierOf(id, tier);
    return at ? reinterpret_cast<const char*>(ReadU32(at + kTierIcon)) : nullptr;
}

const char* ArtifactIcon(const char* collectible)
{
    uintptr_t definition = FindCollectibleDef(collectible);
    return definition ? reinterpret_cast<const char*>(ReadU32(definition + kCollectibleIcon)) : nullptr;
}

bool SetUpgradePrice(const char* id, int tier, int price)
{
    uintptr_t at = TierOf(id, tier);
    if (at)
        *reinterpret_cast<int*>(at) = price;

    return at != 0;
}

bool SetPriceListPrice(const char* list, int index, int price)
{
    uintptr_t definition = FindDef(g_build->PriceListDefs, list);
    uintptr_t at = definition ? ReadU32(definition + kPriceListPrices) + 4 * index : 0;
    if (!definition || index < 0 || at >= ReadU32(definition + kPriceListPrices + 4)) return false;

    *reinterpret_cast<int*>(at) = price;
    return true;
}

}  // namespace game
