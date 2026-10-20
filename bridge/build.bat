@echo off
setlocal
rem vswhere is in the installer's folder: for /f can't run a quoted path with brackets, like "(x86)"
set "PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer;%PATH%"
for /f "usebackq delims=" %%i in (`vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VISUAL_STUDIO=%%i"

if not defined VISUAL_STUDIO (
    echo Visual Studio with the C++ desktop tools was not found.
    exit /b 1
)

call "%VISUAL_STUDIO%\VC\Auxiliary\Build\vcvars32.bat" >nul || exit /b 1

cd /d "%~dp0"
set "OUTPUT=..\build\bridge"
set "MINHOOK=third_party\minhook"

if not exist "%OUTPUT%" mkdir "%OUTPUT%"

set "SOURCES=src\*.cpp %MINHOOK%\src\buffer.c %MINHOOK%\src\hook.c %MINHOOK%\src\trampoline.c %MINHOOK%\src\hde\hde32.c"
set "INCLUDES=/I %MINHOOK%\include /I third_party"
set "COMPILER_OPTIONS=/nologo /LD /O2 /MT /W3 /EHsc /std:c++17 /DWIN32_LEAN_AND_MEAN /DNOMINMAX"
set "LINKER_OPTIONS=/DEF:src\version.def /MACHINE:X86 kernel32.lib user32.lib ws2_32.lib"

cl %COMPILER_OPTIONS% %INCLUDES% %SOURCES% /Fo%OUTPUT%\ /Fe%OUTPUT%\version.dll /link %LINKER_OPTIONS% || exit /b 1

if not exist ..\swd2\bin mkdir ..\swd2\bin
copy /y "%OUTPUT%\version.dll" ..\swd2\bin\version.dll >nul || exit /b 1

echo Built %OUTPUT%\version.dll and copied it to swd2\bin\version.dll
