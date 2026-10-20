"""The Archipelago logo as a texture"""
import pkgutil

from .flags import ICON

ATLAS = "ap-ltf_0"
PNG = f"Atlases/{ATLAS}.png"
INDEX = f"Atlases/{ATLAS}.txt"
MAP = "Atlases/atlases.map.z"
SIZE = 120
ENTRY = f"{ICON} = 0 0 {SIZE} {SIZE}\r\n".encode()


def files() -> dict[str, bytes]:
    return {PNG: pkgutil.get_data(__package__, "ap_logo.png"), INDEX: ENTRY}


def patched_map(raw: bytes) -> bytes:
    if f":{ATLAS}".encode() in raw:
        raise ValueError("atlases.map.z already holds the AP section")

    return raw.rstrip(b"\r\n") + b"\r\n:" + ATLAS.encode() + b"\r\n" + ENTRY
