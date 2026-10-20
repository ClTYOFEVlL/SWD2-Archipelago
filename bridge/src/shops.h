// The workbench sells Archipelago items: at the workbench each tool's row shows the patch's hidden ap_shop_<tool>
// chain instead, so the game's own screen and buy code sell the slots.
#pragma once
#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace shops {

// An upgrade chain's or price list's name -> its prices, in order
using Prices = std::map<std::string, std::vector<int>>;

// The tools screen switches between upgrades (mode 0) and cog mods (mode 1); canBuy only at the workbench. Returns
// true if it refreshed the screen itself, which already ran the game's own mode switch.
bool OnScreenMode(uintptr_t screen, int mode, bool canBuy);

// Writes the client's prices into the loaded definitions: each ap_shop chain's from its tier 2 on, and each price
// list's. Game thread only
void SetPrices(const Prices& upgrades, const Prices& priceLists);

}  // namespace shops
