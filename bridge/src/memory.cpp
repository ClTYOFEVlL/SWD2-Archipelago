#include "memory.h"

#include <windows.h>
#include <cstring>

// __try/__except catches the access violation a bad pointer causes
uint32_t ReadU32(uintptr_t address)
{
    __try {
        return *reinterpret_cast<const uint32_t*>(address);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return 0;
    }
}

float ReadF32(uintptr_t address)
{
    uint32_t bits = ReadU32(address);
    float value;
    memcpy(&value, &bits, 4);
    return value;
}

double ReadF64(uintptr_t address)
{
    uint32_t bits[2] = {ReadU32(address), ReadU32(address + 4)};
    double value;
    memcpy(&value, bits, 8);
    return value;
}

bool ReadCStr(uintptr_t address, char* buffer, size_t capacity)
{
    __try {
        size_t i = 0;
        for (; i + 1 < capacity; ++i) {
            char c = reinterpret_cast<const char*>(address)[i];
            if (c == 0)
                break;
            buffer[i] = (c >= 0x20 && c < 0x7f) ? c : '?';
        }

        buffer[i] = 0;
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        buffer[0] = 0;
        return false;
    }
}

bool ReadGameString(uintptr_t address, char* buffer, size_t capacity)
{
    uint32_t stringCapacity = ReadU32(address + 0x14);
    uintptr_t text = stringCapacity < 16 ? address : ReadU32(address);
    return ReadCStr(text, buffer, capacity);
}
