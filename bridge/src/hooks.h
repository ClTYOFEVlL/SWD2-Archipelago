// Puts the bridge's hooks on the game's functions, with MinHook. hooks.cpp lists every hook.
#pragma once
#include <string>

namespace hooks {

// Returns false, and why, if a hook could not be placed
bool Install(std::string& why);

}  // namespace hooks
