#include "bridge.h"

#include <algorithm>
#include <cstring>
#include <deque>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "game.h"
#include "log.h"
#include "net.h"
#include "nlohmann/json.hpp"
#include "shops.h"
#include "texts.h"

namespace bridge {

namespace {

using json = nlohmann::json;

const char kApLogo[] = "Icons/AP/ap_logo_atlas";  // the atlas entry the patch adds
const char kCogIcon[] = "Icons/Currency/cogs_big";
const char kMoneyIcon[] = "Icons/Currency/money";
const double kBannerSeconds = 4.0;  // how long the game shows a banner, so one at a time

// The save's binding lives in hidden flags, so it rolls back with the save: the seed id and the number of received
// items it holds, as base-256 digits (a flag holds 0 to 255)
const char* const kSeedFlags[] = {"ap_seed_0", "ap_seed_1", "ap_seed_2", "ap_seed_3"};
const char* const kItemFlags[] = {"ap_items_0", "ap_items_1"};

// Carson's and Clifford's price lists, whose purchase counts are checks
const char* const kPriceLists[] = {"carson_cogs", "blueprint_vendor_02"};

// Received items wait until the fall into the Temple, which sets this flag: an early Sprint could skip the earthquake
const char kIntroDoneFlag[] = "ap_temple_lamp";

struct Save {
    int patch = 0;  // ap_save's tier, 0 for a save made without the patch
    uint32_t seed = 0;  // 0 until the save is bound to a slot
    int items = 0;

    const char* State() const { return !patch ? "vanilla" : !seed ? "unbound" : "bound"; }
    bool operator==(const Save& other) const
    {
        return patch == other.patch && seed == other.seed && items == other.items;
    }
};

struct Item {
    std::string kind;  // upgrade, blueprint, artifact, cog or money
    std::string id;  // the upgrade, blueprint or collectible id
    int amount = 0;  // the tier to reach for an upgrade, or how many cogs or dollars
    std::string header, text, icon;
};

struct Banner {
    std::string header, text, icon;
};

// From the client
uint32_t g_clientSeed = 0;  // the seed id of the slot the client last connected to, 0 for none yet
bool g_slotConnected = false;  // the connected client has said which slot it plays
std::vector<Item> g_items;  // every item that slot has received, in order
int g_shown = 0;  // items below this index were shown before, so they're given back silently
std::deque<Banner> g_banners;

// Flags that scripts set during the last frame, applied at the start of this one
std::vector<std::pair<std::string, int>> g_heldFlags;

// What the client was told last
bool g_saveReported = false;
Save g_reportedSave;
bool g_reportAll = true;
std::map<std::string, int, std::less<>> g_reportedFlags;
std::set<std::string> g_reportedTeleporters;
std::map<std::string, int> g_reportedLists;

uintptr_t g_profile = 0;
double g_lastGameTime = -1;
double g_lastBanner = -1e9;
bool g_muted = false;
std::vector<game::Upgrade> g_table;  // this frame's upgrade table, kept to reuse its memory
std::vector<std::string> g_teleporters;

// The client is connected to a slot
void OnConnect(const json& message)
{
    uint32_t seed = message.at("seed").get<uint32_t>();
    if (seed != g_clientSeed) {
        g_items.clear();
        g_shown = 0;
    }

    g_clientSeed = seed;
    g_slotConnected = true;
    g_saveReported = false;
    Log("client connected to the slot with seed id %08X", seed);
}

// The slot's received items from index "start" on, and how many were shown in game before
void OnItems(const json& message)
{
    size_t start = message.at("start").get<size_t>();
    if (start > g_items.size()) {
        Log("items from %u, but only %u are known: ignored (the client must send them all)",
            static_cast<unsigned>(start), static_cast<unsigned>(g_items.size()));
        return;
    }

    g_items.resize(start);
    for (const json& entry : message.at("items")) {
        const json& grant = entry.at("grant");

        Item item;
        item.kind = grant.at("kind").get<std::string>();
        item.id = grant.value("upgrade", grant.value("collectible", ""));
        item.amount = grant.value("tier", grant.value("amount", 0));
        item.header = entry.at("header").get<std::string>();
        item.text = entry.at("text").get<std::string>();
        item.icon = entry.value("icon", "");
        g_items.push_back(item);
    }

    g_shown = std::max(g_shown, message.at("shown").get<int>());
    Log("items: %u received in all, %d shown before", static_cast<unsigned>(g_items.size()), g_shown);
}

void OnTexts(const json& message)
{
    texts::Set(message.at("texts").get<std::map<std::string, std::string>>(),
               message.at("lists").get<std::map<std::string, std::vector<std::string>>>());
}

void OnPrices(const json& message)
{
    shops::SetPrices(message.at("upgrades").get<shops::Prices>(), message.at("pricelists").get<shops::Prices>());
}

void OnBanner(const json& message)
{
    std::string icon = message.value("icon", "");
    g_banners.push_back({message.at("header").get<std::string>(), message.at("text").get<std::string>(),
                         icon.empty() ? kApLogo : icon});
}

void HandleMessages()
{
    std::vector<std::string> lines;
    bool newClient = false;
    net::TakeReceived(lines, newClient);

    // A new client gets told everything, once it says which slot it plays
    if (newClient) {
        g_saveReported = false;
        g_slotConnected = false;
    }

    for (const std::string& line : lines) {
        // false: a line that isn't JSON gives a "discarded" value instead of an exception
        json message = json::parse(line, nullptr, false);
        if (!message.is_object()) {
            Log("unreadable message: %.120s", line.c_str());
            continue;
        }

        // A message missing a field, or with a field of the wrong type, is skipped: at(), get() and value() throw
        std::string type;
        try {
            type = message.value("type", "");
            if (type == "connect")
                OnConnect(message);
            else if (type == "items")
                OnItems(message);
            else if (type == "texts")
                OnTexts(message);
            else if (type == "prices")
                OnPrices(message);
            else if (type == "banner")
                OnBanner(message);
            else
                Log("unknown message type '%s'", type.c_str());
        } catch (const json::exception& error) {
            Log("'%s' message skipped: %s", type.c_str(), error.what());
        }
    }
}

Save ReadSave()
{
    Save save;
    save.patch = game::TierIn(g_table, "ap_save");

    for (int i = 0; i < 4; ++i)
        save.seed |= static_cast<uint32_t>(game::TierIn(g_table, kSeedFlags[i]) & 0xFF) << (8 * i);

    save.items = game::TierIn(g_table, kItemFlags[0]) + 256 * game::TierIn(g_table, kItemFlags[1]);
    return save;
}

// A New Game the patch made takes the connected client's slot
void Bind(const game::Frame& frame)
{
    for (int i = 0; i < 4; ++i)
        game::SetFlag(frame.profile, kSeedFlags[i], (g_clientSeed >> (8 * i)) & 0xFF);

    Log("save bound to the slot with seed id %08X", g_clientSeed);
}

void SetItemCount(const game::Frame& frame, int count)
{
    game::SetFlag(frame.profile, kItemFlags[0], count & 0xFF);
    game::SetFlag(frame.profile, kItemFlags[1], (count >> 8) & 0xFF);
}

std::string IconOf(const Item& item)
{
    const char* icon = nullptr;
    if (!item.icon.empty())
        return item.icon;

    if (item.kind == "upgrade")
        icon = game::UpgradeIcon(item.id.c_str(), item.amount);
    else if (item.kind == "blueprint")
        icon = game::UpgradeIcon(item.id.c_str(), 1);
    else if (item.kind == "artifact")
        icon = game::ArtifactIcon(item.id.c_str());
    else if (item.kind == "cog")
        icon = kCogIcon;
    else if (item.kind == "money")
        icon = kMoneyIcon;

    return icon && *icon ? icon : kApLogo;
}

// Returns false only if the item must be tried again next frame
bool Give(const game::Frame& frame, const Item& item, bool silent)
{
    const char* id = item.id.c_str();

    if (item.kind == "upgrade") {
        // Never lowers a tool
        if (game::TierIn(g_table, id) < item.amount)
            game::SetUpgradeTier(frame, id, item.amount, silent);
    } else if (item.kind == "blueprint") {
        game::GiveBlueprint(frame, id, false);
    } else if (item.kind == "artifact") {
        return game::GiveArtifact(frame, id);
    } else if (item.kind == "cog") {
        game::AddCogs(frame, item.amount, silent);
    } else if (item.kind == "money") {
        game::AddMoney(frame, item.amount, silent);
    } else {
        Log("item of unknown kind '%s': skipped", item.kind.c_str());
    }

    return true;
}

// The item and its count change in the same frame, so a rollback (a death in a cave, Exit to menu) takes both back
void GrantNext(const game::Frame& frame, int index)
{
    const Item& item = g_items[index];
    bool silent = index < g_shown;

    g_muted = true;
    bool given = Give(frame, item, silent);
    g_muted = false;
    if (!given) return;

    SetItemCount(frame, index + 1);
    if (!silent) {
        g_banners.push_back({item.header, item.text, IconOf(item)});
        g_shown = index + 1;
    }

    Log("item %d: %s %s %d%s", index, item.kind.c_str(), item.id.c_str(), item.amount, silent ? " (silent)" : "");
}

bool IsLocationFlag(const char* name)
{
    return !strncmp(name, "ap_loc_", 7) || !strncmp(name, "ap_shop_", 8) || !strcmp(name, "ap_goal");
}

void ReportSave(const Save& save)
{
    if (g_saveReported && save == g_reportedSave) return;

    // Another save, or one that was just bound: report everything it has found
    if (!g_saveReported || save.seed != g_reportedSave.seed || save.patch != g_reportedSave.patch)
        g_reportAll = true;

    g_saveReported = true;
    g_reportedSave = save;
    json report = {{"type", "save"}, {"state", save.State()}, {"seed", save.seed}, {"items", save.items},
                   {"patch", save.patch}};
    net::Send(report.dump());
}

// What the save shows as found: everything after a connect or a save change, then only what's new
void ReportChecks(const game::Frame& frame)
{
    static const char* lists[2] = {game::Intern(kPriceLists[0]), game::Intern(kPriceLists[1])};

    if (g_reportAll) {
        g_reportedFlags.clear();
        g_reportedTeleporters.clear();
        g_reportedLists.clear();
    }

    json flags = json::object();
    json teleporters = json::array();
    json counts = json::object();
    auto addFlag = [&](const char* name, int tier) {
        if (tier <= 0 || !IsLocationFlag(name)) return;

        auto reported = g_reportedFlags.find(name);
        if (reported != g_reportedFlags.end() && reported->second >= tier) return;

        g_reportedFlags[name] = tier;
        flags[name] = tier;
    };

    for (const game::Upgrade& upgrade : g_table)
        addFlag(upgrade.name, upgrade.tier);
    for (const auto& held : g_heldFlags)
        addFlag(held.first.c_str(), held.second);

    game::ReadTeleporters(frame.profile, g_teleporters);
    for (const std::string& name : g_teleporters)
        if (g_reportedTeleporters.insert(name).second)
            teleporters.push_back(name);

    for (int i = 0; i < 2; ++i) {
        int count = game::PriceListCount(frame.profile, lists[i]);
        int& reported = g_reportedLists[kPriceLists[i]];
        if (count > reported) {
            reported = count;
            counts[kPriceLists[i]] = count;
        }
    }

    if (g_reportAll || !flags.empty() || !teleporters.empty() || !counts.empty()) {
        json report = {{"type", "checks"}, {"full", g_reportAll}, {"flags", flags}, {"teleporters", teleporters},
                       {"pricelists", counts}};
        net::Send(report.dump());
    }

    g_reportAll = false;
}

}  // namespace

void OnFrameStart(uintptr_t simulators)
{
    HandleMessages();

    game::Frame frame = game::FrameOf(simulators);
    if (!frame.Valid()) return;

    if (frame.profile != g_profile) {
        // The held flags belonged to the previous profile
        g_heldFlags.clear();
        g_profile = frame.profile;
        texts::SetProfile(frame.profile);
        g_saveReported = false;
    }

    // Game time stands still while the game is paused or unfocused
    double now = game::GameTime(frame.profile);
    bool running = now != g_lastGameTime;
    g_lastGameTime = now;

    if (!net::Connected())
        g_slotConnected = false;

    game::ReadUpgrades(frame.profile, g_table);
    Save save = ReadSave();
    bool ours = save.patch && save.seed && save.seed == g_clientSeed;
    if (net::Connected()) {
        ReportSave(save);
        if (ours && g_slotConnected)
            ReportChecks(frame);
    }

    // Nothing changes while the game is paused or unfocused, or while the player is dead: the game ignores most
    // changes then, and the save is about to roll back
    if (!running || !game::PlayerAlive(frame)) return;

    for (const auto& held : g_heldFlags)
        game::SetFlag(frame.profile, held.first.c_str(), held.second);
    g_heldFlags.clear();

    if (save.patch && !save.seed && g_slotConnected)
        Bind(frame);
    else if (ours && save.items < static_cast<int>(g_items.size()) && game::TierIn(g_table, kIntroDoneFlag) > 0)
        GrantNext(frame, save.items);

    if (!g_banners.empty() && (now - g_lastBanner >= kBannerSeconds || now < g_lastBanner)) {
        const Banner& banner = g_banners.front();
        game::ShowBanner(frame, banner.header.c_str(), banner.text.c_str(), banner.icon.c_str());
        g_banners.pop_front();
        g_lastBanner = now;
    }
}

void OnScriptFlag(const char* id, int tier)
{
    g_heldFlags.emplace_back(id, tier);
    Log("script flag %s = %d (held to the next frame)", id, tier);
}

bool MuteGameBanners()
{
    return g_muted;
}

}  // namespace bridge
