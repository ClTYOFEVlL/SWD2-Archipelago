import hashlib
import json
import pathlib
import pkgutil
import shutil
import subprocess
import sys

import Utils

from . import patcher

GAME_FOLDER = "SteamWorld Dig 2"
STEAM_APP_ID = 571310
EXE = "Dig2.exe"
EXE_SHA256 = "4583a9b1ec614d23ea3503c97a89c0d6e36d88d3292203f409adc1f529d0b5e5"  # the build the bridge supports
DLL = "version.dll"
MARKER = "swd2ap_copy.json"  # what the copy was made from. Only a folder with this file is ever deleted


def copy_dir() -> pathlib.Path:
    return pathlib.Path(Utils.user_path(GAME_FOLDER))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bundled_dll() -> bytes:
    # Inside a zipped apworld a missing file raises OSError
    try:
        data = pkgutil.get_data(__package__, f"bin/{DLL}")
    except OSError:
        data = None

    if not data:
        raise FileNotFoundError(f"the apworld's bin/{DLL} is missing or can't be read")

    return data


def _world_version() -> str:
    return json.loads(pkgutil.get_data(__package__, "archipelago.json"))["world_version"]


def _steam_roots() -> list[pathlib.Path]:
    roots = []

    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                roots.append(pathlib.Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except OSError:
            pass

    roots += [pathlib.Path(r"C:\Program Files (x86)\Steam"), pathlib.Path(r"C:\Program Files\Steam")]
    return roots


def _steam_libraries() -> list[pathlib.Path]:
    libraries = []

    for root in _steam_roots():
        libraries.append(root)

        vdf = root / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue

        for line in vdf.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.strip().split('"')
            if len(parts) >= 4 and parts[1] == "path":
                libraries.append(pathlib.Path(parts[3].replace("\\\\", "\\")))

    return libraries


def find_steam_install() -> pathlib.Path | None:
    for library in _steam_libraries():
        game = library / "steamapps" / "common" / GAME_FOLDER
        if (game / EXE).is_file():
            return game

    return None


def _in_use(dll: pathlib.Path) -> bool:
    # Windows won't open a loaded DLL for writing
    try:
        with open(dll, "r+b"):
            return False
    except FileNotFoundError:
        return False
    except PermissionError:
        return True


def check_source(source: pathlib.Path) -> None:
    exe = source / EXE
    if not exe.is_file():
        raise FileNotFoundError(f"no {EXE} in {source}")

    if _sha256(exe.read_bytes()) != EXE_SHA256:
        raise ValueError(f"{exe} is not the Steam build this integration supports (the bridge would stay off)")

    if patcher.status(source) is not None or (source / DLL).exists():
        raise ValueError(f"{source} has a patch or a {DLL} in it: remove them first, the copy must start vanilla")


def make_patched_copy(source: pathlib.Path, log=print) -> pathlib.Path:
    check_source(source)
    dll = _bundled_dll()
    target = copy_dir()

    if target.exists():
        if not (target / MARKER).is_file():
            raise FileExistsError(f"{target} exists but was not made by this client: move it away first")
        if _in_use(target / DLL):
            raise PermissionError("the patched game is running: close it first")

        log(f"removing the old copy in {target}")
        shutil.rmtree(target)

    log(f"copying {source} to {target}")
    try:
        shutil.copytree(source, target)
        patcher.install(target, log=log)
        (target / DLL).write_bytes(dll)
        (target / "steam_appid.txt").write_text(str(STEAM_APP_ID), encoding="ascii")
    except Exception:
        # A copy without its marker would block every later /auto_patch, so a half-made one goes
        shutil.rmtree(target, ignore_errors=True)
        raise

    marker = {"source": str(source), "world_version": _world_version(), "dll": _sha256(dll)}
    (target / MARKER).write_text(json.dumps(marker, indent=1), encoding="utf-8")
    return target


def copy_problem() -> str | None:
    """Why the copy can't be played as it is, or None."""
    target = copy_dir()
    if not (target / MARKER).is_file():
        return f"there is no patched copy of the game in {target} yet"

    try:
        marker = json.loads((target / MARKER).read_text(encoding="utf-8"))
        made_here = marker["world_version"] == _world_version() and marker["dll"] == _sha256(_bundled_dll())
    except (OSError, ValueError, KeyError) as error:
        return f"the patched copy can't be checked ({error})"

    if not made_here:
        return "the patched copy was made by another version of this apworld"

    try:
        dll_ok = _sha256((target / DLL).read_bytes()) == marker["dll"]
    except OSError:
        dll_ok = False

    if not dll_ok:
        return f"the patched copy's {DLL} is missing or can't be read"

    return None


def launch() -> None:
    target = copy_dir()
    subprocess.Popen([str(target / EXE)], cwd=target)
