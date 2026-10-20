"""Reads the player's game data: Bundle/data01.impak (a zip) and the loose Bundle/**/*.z files."""
import pathlib
import struct
import zipfile
import zlib

PAK = "data01.impak"


# A .z file is the uncompressed size (a little-endian u32), then zlib data
def read_z(data: bytes) -> bytes:
    size = struct.unpack("<I", data[:4])[0]
    raw = zlib.decompress(data[4:])
    if len(raw) != size:
        raise ValueError(f"size mismatch in .z data: header {size}, got {len(raw)}")

    return raw


def write_z(raw: bytes) -> bytes:
    return struct.pack("<I", len(raw)) + zlib.compress(raw, 9)


class GameFiles:
    def __init__(self, game_dir: str | pathlib.Path):
        self.bundle = pathlib.Path(game_dir) / "Bundle"

        pak = self.bundle / PAK
        if not pak.is_file():
            raise FileNotFoundError(f"{pak} not found: is this the SteamWorld Dig 2 folder?")

        self.zip = zipfile.ZipFile(pak)
        self.names = set(self.zip.namelist())

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.zip.close()

    def read(self, path: str) -> bytes:
        if path in self.names:
            return self.zip.read(path)

        loose = self.bundle / (path + ".z")
        if loose.is_file():
            return read_z(loose.read_bytes())

        raise FileNotFoundError(f"{path} is neither in {PAK} nor a loose .z file")

    def text(self, path: str) -> str:
        return self.read(path).decode("utf-8-sig")
