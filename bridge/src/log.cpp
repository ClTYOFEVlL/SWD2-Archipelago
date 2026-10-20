#include "log.h"

#include <windows.h>
#include <cstdarg>
#include <cstdio>
#include <share.h>

static FILE* g_log = nullptr;
static CRITICAL_SECTION g_lock;  // the game thread and the network thread both log

void LogOpen(const wchar_t* path)
{
    InitializeCriticalSection(&g_lock);
    g_log = _wfsopen(path, L"w", _SH_DENYNO);
}

void Log(const char* format, ...)
{
    if (!g_log) return;

    SYSTEMTIME time;
    GetLocalTime(&time);

    EnterCriticalSection(&g_lock);
    fprintf(g_log, "[%02d:%02d:%02d.%03d] ", time.wHour, time.wMinute, time.wSecond, time.wMilliseconds);

    va_list args;
    va_start(args, format);
    vfprintf(g_log, format, args);
    va_end(args);

    fputc('\n', g_log);
    fflush(g_log);
    LeaveCriticalSection(&g_lock);
}
