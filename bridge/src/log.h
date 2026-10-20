// The bridge's log, swd2ap_bridge.log next to the DLL: what it found, what it gave and anything that went wrong. It's
// opened shared, so it can be read while the game runs, and it starts over each time the game starts.
#pragma once

void LogOpen(const wchar_t* path);

// Writes one line with a timestamp, printf style
void Log(const char* format, ...);
