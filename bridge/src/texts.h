// The texts the client sends for the game's text lookup. "%NEXT:<list>%" in a text stands for entry n of that list,
// where n is how many the player bought from that price list (or the Cartographer's rewards paid).
#pragma once
#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace texts {

// Replaces every text. Game thread only
void Set(std::map<std::string, std::string> texts, std::map<std::string, std::vector<std::string>> lists);

// The profile the %NEXT counts are read from
void SetProfile(uintptr_t profile);

// The text to show for an id, as the game's own std::string, or nullptr to let the game look it up. It stays valid
// for the whole run, since the game may keep the pointer
void* Lookup(const char* id);

}  // namespace texts
