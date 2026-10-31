"""``cas.cat`` catalog parsing - maps a chunk's SHA-1 to a .cas file position.

Format (Gibbed ``Gibbed.Frostbite3.VfsFormats/CatalogFile.cs``), confirmed
against every ``cas.cat`` in this install::

    uint64 magic1   = 0x6E61794E6E61794E  ("NyanNyan" little-endian)
    uint64 magic2   = same
    uint32 normalCount
    uint32 patchCount
    uint32 encryptedCount
    int32  unknown1C, unknown20, unknown24     (patch-version related)

    NormalEntry (28 bytes each):
        byte[20] sha1
        uint32   offset          <- byte offset into cas_<DataIndex>.cas
        uint32   size            <- compressed size in bytes
        uint32   tailSize
        uint8    dataIndex       <- cas_<dataIndex:D2>.cas
        uint8    isEncrypted
        byte[2]  zero padding

    EncryptedEntry = NormalEntry + CryptoInfo(uint32 size, char[8] keyId, byte[32] unknown)

    PatchEntry (60 bytes each):
        byte[20] id, byte[20] baseId, byte[20] deltaId

The catalog is *not* obfuscated for MEA (it starts with the NyanNyan magic).
"""
from __future__ import annotations

import struct
from pathlib import Path

from . import filelayer

__all__ = ["CatalogError", "NormalEntry", "PatchEntry", "Catalog", "load_all"]

MAGIC = 0x6E61794E6E61794E


class CatalogError(Exception):
    pass


class NormalEntry:
    __slots__ = ("sha1", "offset", "size", "tail_size", "data_index", "is_encrypted")

    def __init__(self, sha1, offset, size, tail_size, data_index, is_encrypted):
        self.sha1 = sha1
        self.offset = offset
        self.size = size
        self.tail_size = tail_size
        self.data_index = data_index
        self.is_encrypted = is_encrypted

    def __repr__(self):
        return (
            f"NormalEntry(sha1={self.sha1.hex()} offset=0x{self.offset:X} "
            f"size={self.size} tail={self.tail_size} cas={self.data_index})"
        )


class PatchEntry:
    __slots__ = ("id", "base_id", "delta_id")

    def __init__(self, id_, base_id, delta_id):
        self.id = id_
        self.base_id = base_id
        self.delta_id = delta_id

    def __repr__(self):
        return f"PatchEntry({self.id.hex()} = {self.base_id.hex()} + {self.delta_id.hex()})"


class Catalog:
    """One ``cas.cat`` plus the directory its ``cas_*.cas`` files live in."""

    def __init__(self, path: Path):
        self.path = path
        self.directory = path.parent
        self.normal: list[NormalEntry] = []
        self.patches: list[PatchEntry] = []
        self.encrypted: list[tuple[NormalEntry, str]] = []
        self.unknown = (0, 0, 0)
        self._parse()

    def _parse(self) -> None:
        raw = self.path.read_bytes()
        # MEA ships the catalogs inside the DiCE signature layer (0x01CED100)
        data, self.layers = filelayer.strip(raw)
        if len(data) < 32:
            raise CatalogError(f"{self.path}: too small ({len(data)} bytes)")
        magic1, magic2 = struct.unpack_from("<QQ", data, 0)
        if magic1 != MAGIC or magic2 != MAGIC:
            raise CatalogError(
                f"{self.path}: bad magic {magic1:016X}/{magic2:016X} (want {MAGIC:016X}), "
                f"layers={self.layers}"
            )
        normal_count, patch_count, encrypted_count = struct.unpack_from("<III", data, 16)
        self.unknown = struct.unpack_from("<iii", data, 28)

        pos = 40
        for _ in range(normal_count):
            sha1 = data[pos:pos + 20]
            offset, size, tail = struct.unpack_from("<III", data, pos + 20)
            data_index = data[pos + 32]
            is_encrypted = data[pos + 33]
            self.normal.append(
                NormalEntry(sha1, offset, size, tail, data_index, bool(is_encrypted))
            )
            pos += 36

        for _ in range(encrypted_count):
            sha1 = data[pos:pos + 20]
            offset, size, tail = struct.unpack_from("<III", data, pos + 20)
            data_index = data[pos + 32]
            is_encrypted = data[pos + 33]
            entry = NormalEntry(sha1, offset, size, tail, data_index, bool(is_encrypted))
            crypto_size, key_id = struct.unpack_from("<I8s", data, pos + 36)
            self.encrypted.append((entry, key_id.rstrip(b"\x00").decode("ascii", "replace")))
            pos += 36 + 44

        for _ in range(patch_count):
            self.patches.append(
                PatchEntry(data[pos:pos + 20], data[pos + 20:pos + 40], data[pos + 40:pos + 60])
            )
            pos += 60

        if pos != len(data):
            raise CatalogError(
                f"{self.path}: parsed {pos} of {len(data)} bytes "
                f"({normal_count} normal, {encrypted_count} encrypted, {patch_count} patch)"
            )

    def cas_path(self, data_index: int) -> Path:
        return self.directory / f"cas_{data_index:02d}.cas"

    def read_chunk(self, entry: NormalEntry) -> bytes:
        path = self.cas_path(entry.data_index)
        with path.open("rb") as fh:
            fh.seek(entry.offset)
            data = fh.read(entry.size)
        if len(data) != entry.size:
            raise CatalogError(
                f"{path.name}: short read at 0x{entry.offset:X} "
                f"(wanted {entry.size}, got {len(data)})"
            )
        return data


def load_all(search_roots: list[Path]) -> list[Catalog]:
    """Load every ``cas.cat`` under the given roots (each is a separate package)."""
    catalogs = []
    seen = set()
    for root in search_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("cas.cat")):
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            catalogs.append(Catalog(path))
    return catalogs


class CatalogIndex:
    """sha1 -> (catalog, entry) with patch/encrypted variants tracked."""

    def __init__(self, catalogs: list[Catalog]):
        self.catalogs = catalogs
        self.normal: dict[bytes, tuple[Catalog, NormalEntry]] = {}
        self.patches: dict[bytes, tuple[Catalog, PatchEntry]] = {}
        self.encrypted: dict[bytes, tuple[Catalog, NormalEntry, str]] = {}
        for cat in catalogs:
            for entry in cat.normal:
                self.normal.setdefault(entry.sha1, (cat, entry))
            for entry in cat.patches:
                self.patches.setdefault(entry.id, (cat, entry))
            for entry, key_id in cat.encrypted:
                self.encrypted.setdefault(entry.sha1, (cat, entry, key_id))

    @property
    def total_entries(self) -> int:
        return len(self.normal)

    def lookup(self, sha1: bytes):
        """Return a dict describing where the chunk lives, or ``None``."""
        hit = self.normal.get(sha1)
        if hit is not None:
            cat, entry = hit
            return {
                "kind": "normal",
                "catalog": cat,
                "entry": entry,
                "cas": cat.cas_path(entry.data_index),
                "offset": entry.offset,
                "size": entry.size,
            }
        hit = self.encrypted.get(sha1)
        if hit is not None:
            cat, entry, key_id = hit
            return {
                "kind": "encrypted",
                "catalog": cat,
                "entry": entry,
                "cas": cat.cas_path(entry.data_index),
                "offset": entry.offset,
                "size": entry.size,
                "key_id": key_id,
            }
        hit = self.patches.get(sha1)
        if hit is not None:
            cat, entry = hit
            return {
                "kind": "patch",
                "catalog": cat,
                "entry": entry,
                "cas": None,
                "offset": None,
                "size": None,
            }
        return None
