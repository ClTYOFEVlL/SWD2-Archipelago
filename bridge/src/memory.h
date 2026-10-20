// Guarded reads of the game's memory. A pointer can be stale while a level loads, so a read that faults gives 0 (or
// an empty string) instead of crashing the game.
#pragma once
#include <cstddef>
#include <cstdint>

uint32_t ReadU32(uintptr_t address);
float ReadF32(uintptr_t address);
double ReadF64(uintptr_t address);

// A C string, printable ASCII only (anything else becomes '?'). Returns false and "" if it can't be read
bool ReadCStr(uintptr_t address, char* buffer, size_t capacity);

// The game's std::string (MSVC 2010, 0x1C bytes): the text inline at +0 when its capacity (at +0x14) is under 16,
// otherwise a pointer to it at +0, and the length at +0x10
bool ReadGameString(uintptr_t address, char* buffer, size_t capacity);
