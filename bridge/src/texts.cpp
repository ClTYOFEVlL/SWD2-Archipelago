#include "texts.h"

#include <windows.h>
#include <cstdlib>
#include <cstring>

#include "game.h"
#include "log.h"
#include "memory.h"

namespace texts {

namespace {

// The Cartographer's reward thresholds (collectors.xml). The profile keeps the threshold of the last one paid
const int kCartographerThresholds[] = {1, 3, 6, 10, 15, 21, 28, 42};
const char kCartographer[] = "cartographer";

struct List {
    const char* id = nullptr;  // the price list's interned id, or none for the Cartographer
    std::vector<std::string> entries;
};

SRWLOCK g_lock = SRWLOCK_INIT;  // the game may look texts up off the game thread
std::map<std::string, std::string, std::less<>> g_texts;
std::map<std::string, List, std::less<>> g_lists;
std::map<std::string, char*> g_shown;  // every text handed to the game -> its game string, kept for the whole run
volatile uintptr_t g_profile = 0;

// The game's std::string (MSVC 2010, memory.h), with padding on both sides
char* MakeGameString(const std::string& text)
{
    char* memory = static_cast<char*>(calloc(1, 0x40));
    char* string = memory + 8;
    size_t length = text.size();

    if (length < 16) {
        memcpy(string, text.c_str(), length + 1);
        *reinterpret_cast<uint32_t*>(string + 0x14) = 15;
    } else {
        *reinterpret_cast<char**>(string) = _strdup(text.c_str());
        *reinterpret_cast<uint32_t*>(string + 0x14) = static_cast<uint32_t>(length);
    }

    *reinterpret_cast<uint32_t*>(string + 0x10) = static_cast<uint32_t>(length);
    return string;
}

size_t NextIndex(const std::string& name, const List& list)
{
    uintptr_t profile = g_profile;
    if (!profile) return 0;

    if (name != kCartographer)
        return static_cast<size_t>(game::PriceListCount(profile, list.id));

    int paid = game::CartographerPaid(profile);
    size_t next = 0;
    while (next < 8 && kCartographerThresholds[next] <= paid)
        ++next;

    return next;
}

// Fills in every "%NEXT:<list>%", or removes it once the list is bought out
std::string Expand(const std::string& text)
{
    std::string result;
    size_t at = 0;

    for (;;) {
        size_t start = text.find("%NEXT:", at);
        size_t stop = start == std::string::npos ? start : text.find('%', start + 6);
        if (stop == std::string::npos)
            break;

        result.append(text, at, start - at);

        auto list = g_lists.find(text.substr(start + 6, stop - start - 6));
        if (list != g_lists.end()) {
            size_t next = NextIndex(list->first, list->second);
            if (next < list->second.entries.size())
                result += list->second.entries[next];
        }

        at = stop + 1;
    }

    result.append(text, at, std::string::npos);
    return result;
}

}  // namespace

void Set(std::map<std::string, std::string> texts, std::map<std::string, std::vector<std::string>> lists)
{
    std::map<std::string, List, std::less<>> newLists;
    for (auto& entry : lists) {
        List& list = newLists[entry.first];

        // Interning changes the engine's string pool: game thread only
        if (entry.first != kCartographer)
            list.id = game::Intern(entry.first.c_str());

        list.entries = std::move(entry.second);
    }

    AcquireSRWLockExclusive(&g_lock);
    g_texts.clear();
    for (auto& text : texts)
        g_texts.emplace(text.first, std::move(text.second));
    g_lists = std::move(newLists);
    ReleaseSRWLockExclusive(&g_lock);

    Log("texts: %u texts, %u lists", static_cast<unsigned>(texts.size()), static_cast<unsigned>(lists.size()));
}

void SetProfile(uintptr_t profile)
{
    g_profile = profile;
}

void* Lookup(const char* id)
{
    char name[128];
    if (!ReadCStr(reinterpret_cast<uintptr_t>(id), name, sizeof(name)) || !name[0]) return nullptr;

    void* result = nullptr;

    AcquireSRWLockExclusive(&g_lock);
    auto text = g_texts.find(name);
    if (text != g_texts.end()) {
        std::string shown = Expand(text->second);

        auto made = g_shown.find(shown);
        if (made == g_shown.end())
            made = g_shown.emplace(shown, MakeGameString(shown)).first;

        result = made->second;
    }
    ReleaseSRWLockExclusive(&g_lock);

    return result;
}

}  // namespace texts
