"""The Archipelago logo as a texture, and greyed copies of the game's own tool icons"""
import pkgutil
import struct
import xml.etree.ElementTree as ET
import zlib

from ..data import ITEMS
from .flags import ICON, waiting_icon

ATLAS = "ap-ltf_0"
PNG = f"Atlases/{ATLAS}.png"
INDEX = f"Atlases/{ATLAS}.txt"
MAP = "Atlases/atlases.map.z"
SIZE = 120
ENTRY = f"{ICON} = 0 0 {SIZE} {SIZE}\r\n".encode()

GAME_ICONS = "icons-ltf_0"
GAME_ICONS_PNG = f"Atlases/{GAME_ICONS}.png"  # a loose file, not in the pak
WAITING = "ap-waiting-ltf_0"

# The tools whose progressive copies can wait for a main item
_WAITING_ITEMS = {item.grant.progressive for item in ITEMS if item.grant.kind == "main"}
WAITING_TOOLS = [item.grant.upgrade for item in ITEMS if item.name in _WAITING_ITEMS]


def files(waiting_png: bytes, waiting_index: bytes) -> dict[str, bytes]:
    return {
        PNG: pkgutil.get_data(__package__, "ap_logo.png"),
        INDEX: ENTRY,
        f"Atlases/{WAITING}.png": waiting_png,
        f"Atlases/{WAITING}.txt": waiting_index,
    }


def patched_map(raw: bytes, waiting_index: bytes) -> bytes:
    if f":{ATLAS}".encode() in raw:
        raise ValueError("atlases.map.z already holds the AP section")

    sections = b":" + ATLAS.encode() + b"\r\n" + ENTRY + b":" + WAITING.encode() + b"\r\n" + waiting_index
    return raw.rstrip(b"\r\n") + b"\r\n" + sections


def waiting_icons(icons_png: bytes, upgrades: str, atlas_map: bytes) -> tuple[bytes, bytes]:
    """The waiting tools tier icons greyed, cut from the game's icons atlas."""
    rows = _read_png(icons_png)
    places = _places(atlas_map.decode("utf-8"), GAME_ICONS)

    icons = []
    for upgrade in ET.fromstring(upgrades).iter("Upgrade"):
        if upgrade.get("Name") in WAITING_TOOLS:
            for tier, element in enumerate(upgrade.findall("Tier"), 1):
                icons.append((waiting_icon(upgrade.get("Name"), tier), places[element.findtext("Icon")]))

    # The icons side by side in one row
    height = max(place[3] for _, place in icons)
    texture = [bytearray(4 * sum(place[2] for _, place in icons)) for _ in range(height)]
    index = []
    left = 0
    for name, (x, y, w, h) in icons:
        for row in range(h):
            texture[row][4 * left:4 * (left + w)] = _greyed(rows[y + row][4 * x:4 * (x + w)])
        index.append(f"{name} = {left} 0 {w} {h}\r\n")
        left += w

    return _write_png(left, texture), "".join(index).encode()


def _places(atlas_map: str, atlas: str) -> dict[str, tuple[int, int, int, int]]:
    """Each entry of one atlas in atlases.map: name -> (x, y, width, height)."""
    places = {}
    section = None
    for line in atlas_map.splitlines():
        if line.startswith(":"):
            section = line[1:]
        elif section == atlas and " = " in line:
            name, _, place = line.partition(" = ")
            places[name] = tuple(int(number) for number in place.split())

    return places


def _greyed(pixels: bytes) -> bytes:
    # Grey and a little darker, the alpha kept
    out = bytearray(pixels)
    for i in range(0, len(out), 4):
        red, green, blue = out[i:i + 3]
        grey = (red * 299 + green * 587 + blue * 114) * 6 // 10000
        out[i:i + 3] = bytes((grey, grey, grey))

    return bytes(out)


def _read_png(data: bytes) -> list[bytes]:
    """The rows of pixels of an 8-bit RGBA PNG stored unfiltered, as the game's atlases are."""
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", data[16:29])
    if (depth, colour, interlace) != (8, 6, 0):
        raise ValueError("the game's icons atlas isn't an 8-bit RGBA PNG")

    compressed = b""
    at = 8
    while at < len(data):
        length, kind = struct.unpack(">I4s", data[at:at + 8])
        if kind == b"IDAT":
            compressed += data[at + 8:at + 8 + length]
        at += 12 + length

    raw = zlib.decompress(compressed)
    stride = 1 + 4 * width
    if any(raw[y * stride] for y in range(height)):
        raise ValueError("the game's icons atlas uses PNG filters")

    return [raw[y * stride + 1:(y + 1) * stride] for y in range(height)]


def _write_png(width: int, rows: list[bytearray]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, len(rows), 8, 6, 0, 0, 0)
    pixels = zlib.compress(b"".join(b"\0" + bytes(row) for row in rows))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
