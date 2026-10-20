// The bridge DLL, which the game loads as version.dll.
#include <windows.h>
#include <string>

#include "game.h"
#include "hooks.h"
#include "log.h"
#include "memory.h"
#include "net.h"
#include "nlohmann/json.hpp"

bool LoadRealVersionDll();  // version_proxy.cpp

namespace {

const int kProtocolVersion = 1;  // sent in the hello message: the client refuses a bridge it doesn't know

uintptr_t g_exeStart = 0;
uintptr_t g_exeEnd = 0;

// Logs a crash inside Dig2.exe for bug reports. The game's own crash handling runs after it
LONG CALLBACK CrashLog(PEXCEPTION_POINTERS info)
{
    uintptr_t at = reinterpret_cast<uintptr_t>(info->ExceptionRecord->ExceptionAddress);
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || at < g_exeStart || at >= g_exeEnd)
        return EXCEPTION_CONTINUE_SEARCH;

    const CONTEXT* registers = info->ContextRecord;
    Log("CRASH in Dig2.exe at +%X: EAX=%08X EBX=%08X ECX=%08X EDX=%08X ESI=%08X EDI=%08X EBP=%08X ESP=%08X",
        static_cast<unsigned>(at - g_exeStart), registers->Eax, registers->Ebx, registers->Ecx, registers->Edx,
        registers->Esi, registers->Edi, registers->Ebp, registers->Esp);

    for (int i = 0; i < 8; ++i)
        Log("  stack+%02X: %08X", i * 4, ReadU32(registers->Esp + i * 4));

    return EXCEPTION_CONTINUE_SEARCH;
}

DWORD WINAPI Start(LPVOID)
{
    std::string why;
    bool ok = game::Init(why) && hooks::Install(why);

    if (ok) {
        g_exeStart = game::At(0);
        auto dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(g_exeStart);
        auto nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(g_exeStart + dos->e_lfanew);
        g_exeEnd = g_exeStart + nt->OptionalHeader.SizeOfImage;

        AddVectoredExceptionHandler(1, CrashLog);
    } else {
        Log("the bridge is off: %s", why.c_str());
    }

    nlohmann::json hello = {{"type", "hello"}, {"protocol", kProtocolVersion}, {"game_ok", ok}, {"error", why}};
    net::Run(hello.dump());
    return 0;
}

}  // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason != DLL_PROCESS_ATTACH) return TRUE;

    DisableThreadLibraryCalls(module);

    wchar_t path[MAX_PATH];
    GetModuleFileNameW(module, path, MAX_PATH);
    wchar_t* slash = wcsrchr(path, L'\\');
    if (slash)
        lstrcpyW(slash + 1, L"swd2ap_bridge.log");
    LogOpen(path);

    bool real = LoadRealVersionDll();
    Log("SteamWorld Dig 2 Archipelago bridge, protocol %d (the system's version.dll: %s)", kProtocolVersion,
        real ? "loaded" : "MISSING");

    CreateThread(nullptr, 0, Start, nullptr, 0, nullptr);
    return TRUE;
}
