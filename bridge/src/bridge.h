// The bridge's work, on the game thread at the start of each frame.
#pragma once
#include <cstdint>

namespace bridge {

void OnFrameStart(uintptr_t simulators);

// A script set an "ap_" flag: reported at once, applied at the start of the next frame (hooks.cpp says why)
void OnScriptFlag(const char* id, int tier);

// True while the bridge gives an item, so the game's own banner is dropped
bool MuteGameBanners();

}  // namespace bridge
