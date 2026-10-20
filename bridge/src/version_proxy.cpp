// Forwards every function to the system's version.dll. The game's SDL2.dll imports it, and Windows loads a copy next
// to Dig2.exe first.
#include <windows.h>

#define VERSION_EXPORTS(X)            \
    X(GetFileVersionInfoA)            \
    X(GetFileVersionInfoByHandle)     \
    X(GetFileVersionInfoExA)          \
    X(GetFileVersionInfoExW)          \
    X(GetFileVersionInfoSizeA)        \
    X(GetFileVersionInfoSizeExA)      \
    X(GetFileVersionInfoSizeExW)      \
    X(GetFileVersionInfoSizeW)        \
    X(GetFileVersionInfoW)            \
    X(VerFindFileA)                   \
    X(VerFindFileW)                   \
    X(VerInstallFileA)                \
    X(VerInstallFileW)                \
    X(VerLanguageNameA)               \
    X(VerLanguageNameW)               \
    X(VerQueryValueA)                 \
    X(VerQueryValueW)

#define DECLARE_SLOT(name) static FARPROC g_##name = nullptr;
VERSION_EXPORTS(DECLARE_SLOT)

// Each export jumps straight to the real function, so the arguments pass through untouched
#define DEFINE_STUB(name) \
    extern "C" __declspec(naked) void Proxy_##name() { __asm { jmp dword ptr [g_##name] } }
VERSION_EXPORTS(DEFINE_STUB)

static HMODULE g_realVersion = nullptr;

bool LoadRealVersionDll()
{
    wchar_t path[MAX_PATH];
    UINT length = GetSystemDirectoryW(path, MAX_PATH);
    if (length == 0 || length > MAX_PATH - 16) return false;

    lstrcatW(path, L"\\version.dll");
    g_realVersion = LoadLibraryW(path);
    if (!g_realVersion) return false;

#define RESOLVE(name) g_##name = GetProcAddress(g_realVersion, #name);
    VERSION_EXPORTS(RESOLVE)
    return true;
}
