// Every hook on the game's functions. A __thiscall function gets a __fastcall detour: the object arrives in ecx.
#include "hooks.h"

#include <cstdint>
#include <cstring>

#include "MinHook.h"
#include "bridge.h"
#include "game.h"
#include "log.h"
#include "shops.h"
#include "texts.h"

namespace hooks {

namespace {

// Runs once a frame, also while paused. Upgrades only change here, before the simulators: changed later in a frame,
// the next pickaxe swing can crash the game
typedef void(__stdcall* SimulatorsUpdateFn)(void* simulators, void* frameTime, void* p3);
SimulatorsUpdateFn g_simulatorsUpdate;

void __stdcall SimulatorsUpdate(void* simulators, void* frameTime, void* p3)
{
    bridge::OnFrameStart(reinterpret_cast<uintptr_t>(simulators));
    g_simulatorsUpdate(simulators, frameTime, p3);
}

// The SetUpgrade script node, which always returns true (on to the next node). The patch's locations set "ap_" flags
// with it mid-frame, so the bridge takes them and sets them next frame
const uintptr_t kNodeUpgradeId = 0xC0;
const uintptr_t kNodeTier = 0xC4;

typedef int(__thiscall* SetUpgradeNodeFn)(void* scriptSimulator, uint8_t* node);
SetUpgradeNodeFn g_setUpgradeNode;

int __fastcall SetUpgradeNode(void* scriptSimulator, void*, uint8_t* node)
{
    const char* id = *reinterpret_cast<const char**>(node + kNodeUpgradeId);
    if (id && !strncmp(id, "ap_", 3)) {
        bridge::OnScriptFlag(id, *reinterpret_cast<int*>(node + kNodeTier));
        return 1;
    }

    return g_setUpgradeNode(scriptSimulator, node);
}

typedef void(__thiscall* ToolsScreenModeFn)(void* screen, int mode, int canBuy);
ToolsScreenModeFn g_toolsScreenMode;

void __fastcall ToolsScreenMode(void* screen, void*, int mode, int canBuy)
{
    if (!shops::OnScreenMode(reinterpret_cast<uintptr_t>(screen), mode, (canBuy & 0xFF) != 0))
        g_toolsScreenMode(screen, mode, canBuy);
}

typedef void*(__thiscall* LocalizeFn)(void* handler, const char* id);
LocalizeFn g_localize;

void* __fastcall Localize(void* handler, void*, const char* id)
{
    void* text = texts::Lookup(id);
    return text ? text : g_localize(handler, id);
}

// The Cartographer's rewards and the podiums give "ap_" flags this way: the game's banner ("Equip at workbench")
// would be wrong for them
typedef void(__stdcall* GiveBlueprintFn)(void* playerSimulator, const char* id, int banner);
GiveBlueprintFn g_giveBlueprint;

void __stdcall GiveBlueprint(void* playerSimulator, const char* id, int banner)
{
    if (id && !strncmp(id, "ap_", 3))
        banner = 0;

    g_giveBlueprint(playerSimulator, id, banner);
}

// Dropped while the bridge gives an item, and for a podium's "Got <upgrade>!" (banner_gain_ability): podiums give
// nameless flags, and the client's banner says what was found
typedef void(__stdcall* BannerShowFn)(void* ui, const char* key, const char* headerId, const char* headerArg,
                                      const char* textId, const char* textArg, const char* icon);
BannerShowFn g_bannerShow;

void __stdcall BannerShow(void* ui, const char* key, const char* headerId, const char* headerArg, const char* textId,
                          const char* textArg, const char* icon)
{
    bool podium = key && !strcmp(key, "banner_gain_ability");
    if (!bridge::MuteGameBanners() && !podium)
        g_bannerShow(ui, key, headerId, headerArg, textId, textArg, icon);
}

// The answer to the pause menu's Self-Destruct question, 0 for yes. Yes sets the player's health to 0
typedef void(__thiscall* SelfDestructFn)(void* menu, int button);
SelfDestructFn g_selfDestruct;

void __fastcall SelfDestruct(void* menu, void*, int button)
{
    if (button == 0)
        bridge::OnSelfDestruct();

    g_selfDestruct(menu, button);
}

struct Hook {
    uintptr_t offset;
    void* detour;
    void** original;  // where MinHook stores the way to call the original
    const char* name;
};

template <typename Detour, typename Original>
Hook MakeHook(uintptr_t offset, Detour detour, Original* original, const char* name)
{
    return {offset, reinterpret_cast<void*>(detour), reinterpret_cast<void**>(original), name};
}

}  // namespace

bool Install(std::string& why)
{
    const Hook all[] = {
        MakeHook(game::g_build->SimulatorsUpdate, &SimulatorsUpdate, &g_simulatorsUpdate, "Simulators::Update"),
        MakeHook(game::g_build->SetUpgradeNode, &SetUpgradeNode, &g_setUpgradeNode, "SetUpgrade node"),
        MakeHook(game::g_build->ToolsScreenMode, &ToolsScreenMode, &g_toolsScreenMode, "ToolsScreen mode"),
        MakeHook(game::g_build->Localize, &Localize, &g_localize, "Localize"),
        MakeHook(game::g_build->GiveBlueprint, &GiveBlueprint, &g_giveBlueprint, "GiveBlueprint"),
        MakeHook(game::g_build->BannerShow, &BannerShow, &g_bannerShow, "BannerUI::Show"),
        MakeHook(game::g_build->SelfDestruct, &SelfDestruct, &g_selfDestruct, "Self-Destruct"),
    };

    if (MH_Initialize() != MH_OK) {
        why = "MinHook did not start";
        return false;
    }

    for (const Hook& hook : all) {
        if (MH_CreateHook(reinterpret_cast<void*>(game::At(hook.offset)), hook.detour, hook.original) != MH_OK) {
            why = std::string("could not hook ") + hook.name;
            return false;
        }
    }

    if (MH_EnableHook(MH_ALL_HOOKS) != MH_OK) {
        why = "could not enable the hooks";
        return false;
    }

    Log("%u hooks in place", static_cast<unsigned>(sizeof(all) / sizeof(all[0])));
    return true;
}

}  // namespace hooks
