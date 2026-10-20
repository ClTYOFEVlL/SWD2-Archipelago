#include "shops.h"

#include <cstdio>

#include "game.h"
#include "log.h"
#include "memory.h"

namespace shops {

namespace {

const char* const kTools[] = {
    "pickaxe", "backpack", "lamp", "armor", "watertank", "pressurebomb", "jackhammer", "steampack",
};
const int kToolCount = 8;

// The tools screen's rows
const uintptr_t kRowPointerSize = 8;
const uintptr_t kMaxRows = 64;

// Each tool's upgrade definition and its ap_shop chain, found once the game has loaded its definitions
uintptr_t g_tools[kToolCount];
uintptr_t g_chains[kToolCount];

typedef void(__stdcall* RefreshFn)(uintptr_t screen, int initial);

bool FindDefinitions()
{
    if (g_tools[0] && g_chains[0]) return true;

    for (int i = 0; i < kToolCount; ++i) {
        char chain[64];
        sprintf_s(chain, "ap_shop_%s", kTools[i]);

        g_tools[i] = game::FindUpgradeDef(kTools[i]);
        g_chains[i] = game::FindUpgradeDef(chain);

        if (!g_tools[i] || !g_chains[i]) {
            Log("shops: %s or %s is not defined (is the patch installed?)", kTools[i], chain);
            g_tools[0] = 0;  // look again next time
            return false;
        }
    }

    return true;
}

}  // namespace

bool OnScreenMode(uintptr_t screen, int mode, bool canBuy)
{
    if (!FindDefinitions()) return false;

    // On the workbench's upgrades page each tool's row shows its chain, and everywhere else the tool
    bool selling = mode == 0 && canBuy;
    int changed = 0;

    uintptr_t rowsBegin = ReadU32(screen + game::g_build->ScreenRows);
    uintptr_t rowsEnd = ReadU32(screen + game::g_build->ScreenRows + 4);
    uintptr_t rowsLimit = rowsBegin + kRowPointerSize * kMaxRows;

    for (uintptr_t it = rowsBegin; it < rowsEnd && it < rowsLimit; it += kRowPointerSize) {
        uintptr_t row = ReadU32(it);
        if (!row) continue;

        uintptr_t shown = ReadU32(row + game::g_build->RowDefinition);

        for (int i = 0; i < kToolCount; ++i) {
            uintptr_t from = selling ? g_tools[i] : g_chains[i];
            uintptr_t to = selling ? g_chains[i] : g_tools[i];

            if (shown == from) {
                *reinterpret_cast<uintptr_t*>(row + game::g_build->RowDefinition) = to;
                ++changed;
            }
        }
    }

    if (!changed) return false;

    // Refresh the screen ourselves. It reads every row again from its definition, then runs the mode switch, which
    // changes nothing by now
    *reinterpret_cast<uint32_t*>(screen + game::g_build->ScreenMode) = mode;
    *reinterpret_cast<uint8_t*>(screen + game::g_build->ScreenCanBuy) = canBuy ? 1 : 0;
    reinterpret_cast<RefreshFn>(game::At(game::g_build->ToolsScreenRefresh))(screen, 1);

    return true;
}

void SetPrices(const Prices& upgrades, const Prices& priceLists)
{
    int written = 0;
    int missing = 0;

    for (const auto& [chain, prices] : upgrades) {
        // Tier 1 means nothing bought yet, so the first paid tier is tier 2
        for (size_t i = 0; i < prices.size(); ++i) {
            int tier = static_cast<int>(i) + 2;

            if (game::SetUpgradePrice(chain.c_str(), tier, prices[i]))
                ++written;
            else
                ++missing;
        }
    }

    for (const auto& [list, prices] : priceLists) {
        for (size_t i = 0; i < prices.size(); ++i) {
            int index = static_cast<int>(i);

            if (game::SetPriceListPrice(list.c_str(), index, prices[i]))
                ++written;
            else
                ++missing;
        }
    }

    Log("prices: %d written, %d not found", written, missing);
}

}  // namespace shops
