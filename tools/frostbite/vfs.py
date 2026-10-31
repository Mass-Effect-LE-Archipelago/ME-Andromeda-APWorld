"""High-level view of the Mass Effect Andromeda Frostbite container.

Ties together the pieces:

    layout.toc / .sb / .toc  ->  asset name, sha1, compressed + original size
    cas.cat                  ->  sha1 to (cas_XX.cas, offset, size)
    .cas bytes               ->  Frostbite block decompression
    decompressed bytes       ->  EBX partition (GUIDs live here)

Source priority follows the game's own patch order: ``Patch`` shadows
``Update``, which shadows ``Data``.  Nothing in here ever writes to the game
directory; all reads are bounded.
"""
from __future__ import annotations

import gzip
import os
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

from . import catalog, compress, dbobject, filelayer, partition, patch

__all__ = [
    "DEFAULT_GAME_ROOT",
    "ROOTS",
    "AssetRecord",
    "Game",
    "AssetError",
]

DEFAULT_GAME_ROOT = Path(r"C:\Steam\steamapps\common\Mass Effect Andromeda")

#: directory name -> priority (lower wins)
ROOTS = {"patch": 0, "update": 1, "data": 2}
_ROOT_DIRS = {"patch": "Patch", "update": "Update", "data": "Data"}

_CACHE_VERSION = 4


class AssetError(Exception):
    """Raised when an asset cannot be resolved or read, with a human reason."""


@dataclass(frozen=True)
class AssetRecord:
    name: str
    kind: str          # 'ebx' | 'res'
    sha1: bytes
    size: int          # bytes of cas data (compressed)
    original_size: int  # bytes after decompression
    sb_path: str       # superbundle that lists it, relative to the game root
    bundle: str        # bundle path inside the superbundle
    root: str          # 'data' | 'patch' | 'update'

    @property
    def priority(self) -> int:
        return ROOTS[self.root]

    def describe(self) -> str:
        return (
            f"{self.name}  sha1={self.sha1.hex()}  size={self.size}  "
            f"originalSize={self.original_size}  [{self.kind}] {self.sb_path}"
        )


class Game:
    """A read-only handle on the game install."""

    def __init__(self, root: Path | str = DEFAULT_GAME_ROOT,
                 roots: tuple[str, ...] = ("patch", "update", "data"),
                 use_cache: bool = True, verbose: bool = False):
        self.root = Path(root)
        if not self.root.is_dir():
            raise AssetError(f"game root not found: {self.root}")
        self.roots = tuple(r for r in ("patch", "update", "data") if r in roots)
        self.verbose = verbose
        self.use_cache = use_cache
        self._index: dict[str, list[AssetRecord]] | None = None
        self._catalog_index: catalog.CatalogIndex | None = None
        self.stats: dict[str, int] = {}

    # -- superbundle index --------------------------------------------------
    def _sb_files(self) -> list[Path]:
        files: list[Path] = []
        for r in self.roots:
            base = self.root / _ROOT_DIRS[r]
            if base.is_dir():
                files.extend(sorted(base.rglob("*.sb")))
        files.sort(key=lambda p: (self._root_of(p), str(p)))
        return files

    def _root_of(self, path: Path) -> int:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return 99
        top = rel.parts[0].lower() if rel.parts else ""
        return ROOTS.get(top, 99)

    def _root_name_of(self, path: Path) -> str:
        rel = path.relative_to(self.root)
        top = rel.parts[0].lower() if rel.parts else ""
        return top if top in ROOTS else "data"

    def _fingerprint(self) -> str:
        parts = []
        for path in self._sb_files():
            st = path.stat()
            parts.append(f"{path}|{st.st_size}|{st.st_mtime_ns}")
        return "|".join(parts)

    @property
    def cache_path(self) -> Path:
        return Path(__file__).with_name("_cache") / "sb-index.pickle.gz"

    def index(self, rebuild: bool = False) -> dict[str, list[AssetRecord]]:
        if self._index is not None and not rebuild:
            return self._index

        fingerprint = self._fingerprint()
        if self.use_cache and not rebuild and self.cache_path.is_file():
            try:
                with gzip.open(self.cache_path, "rb") as fh:
                    blob = pickle.load(fh)
                if (blob.get("version") == _CACHE_VERSION
                        and blob.get("fingerprint") == fingerprint
                        and blob.get("roots") == self.roots):
                    self._index = {
                        name: [AssetRecord(*row) for row in rows]
                        for name, rows in blob["index"].items()
                    }
                    self.stats["cache"] = 1
                    self.stats["sb_files"] = len(self._sb_files())
                    self.stats["names"] = len(self._index)
                    self.stats["listings"] = sum(len(v) for v in self._index.values())
                    return self._index
            except Exception:
                pass  # corrupt/old cache -> rebuild

        start = time.time()
        index: dict[str, list[AssetRecord]] = {}
        sb_count = 0
        entries = 0
        for path in self._sb_files():
            sb_count += 1
            rel = str(path.relative_to(self.root)).replace("\\", "/")
            root_name = self._root_name_of(path)
            try:
                body, _layers = filelayer.strip(path.read_bytes())
                obj = dbobject.parse(body)
            except (filelayer.FileLayerError, dbobject.DbObjectError) as exc:
                raise AssetError(f"{rel}: {exc}") from exc
            for bundle in obj.get("bundles") or []:
                bundle_path = bundle.get("path") or ""
                for kind, key in (("ebx", "ebx"), ("res", "res")):
                    for entry in bundle.get(key) or []:
                        name = entry.get("name")
                        sha1 = entry.get("sha1")
                        if not name or not isinstance(sha1, bytes) or len(sha1) != 20:
                            continue
                        record = AssetRecord(
                            name=name,
                            kind=kind,
                            sha1=sha1,
                            size=int(entry.get("size") or 0),
                            original_size=int(entry.get("originalSize") or 0),
                            sb_path=rel,
                            bundle=bundle_path,
                            root=root_name,
                        )
                        index.setdefault(name.lower(), []).append(record)
                        entries += 1

        # sort each name's records so the highest-priority source comes first
        for records in index.values():
            records.sort(key=lambda r: (r.priority, r.kind != "ebx", r.sb_path))

        self.stats.update(
            sb_files=sb_count,
            listings=entries,
            names=len(index),
            seconds=round(time.time() - start, 1),
        )
        self._index = index
        if self.use_cache:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.cache_path.with_suffix(".tmp")
                # store plain tuples so the cache does not depend on how the
                # package was imported (frostbite.vfs vs tools.frostbite.vfs)
                plain = {
                    name: [
                        (r.name, r.kind, r.sha1, r.size, r.original_size,
                         r.sb_path, r.bundle, r.root)
                        for r in records
                    ]
                    for name, records in index.items()
                }
                with gzip.open(tmp, "wb", compresslevel=6) as fh:
                    pickle.dump(
                        {
                            "version": _CACHE_VERSION,
                            "fingerprint": fingerprint,
                            "roots": self.roots,
                            "index": plain,
                        },
                        fh,
                        protocol=pickle.HIGHEST_PROTOCOL,
                    )
                os.replace(tmp, self.cache_path)
            except OSError:
                pass
        return self._index

    # -- lookups ------------------------------------------------------------
    def find(self, name: str) -> list[AssetRecord]:
        return list(self.index().get(name.strip().replace("\\", "/").lower(), []))

    def resolve(self, name: str) -> AssetRecord:
        records = self.find(name)
        if not records:
            raise AssetError(f"asset not found in any superbundle: {name}")
        return records[0]

    def iter_names(self, substring: str | None = None):
        needle = substring.lower() if substring else None
        for name in sorted(self.index()):
            if needle is None or needle in name:
                yield name

    # -- catalogs -----------------------------------------------------------
    def catalogs(self) -> catalog.CatalogIndex:
        if self._catalog_index is None:
            dirs = [self.root / _ROOT_DIRS[r] for r in self.roots]
            dirs.append(self.root / "Update")
            cats = catalog.load_all(dirs)
            if not cats:
                raise AssetError(f"no cas.cat found under {self.root}")
            self._catalog_index = catalog.CatalogIndex(cats)
        return self._catalog_index

    def locate(self, record: AssetRecord) -> dict:
        """Map a record's sha1 to a concrete cas file position."""
        index = self.catalogs()
        hit = index.lookup(record.sha1)
        if hit is None:
            raise AssetError(
                f"sha1 {record.sha1.hex()} ({record.name}) is not in any cas.cat "
                f"({index.total_entries} unique chunks searched)"
            )
        return hit

    def chunk_data(self, record: AssetRecord) -> tuple[bytes, dict]:
        """Read and decompress a record's payload.  Returns (bytes, location)."""
        return self._chunk_data(record, depth=0)

    def _chunk_data(self, record: AssetRecord, depth: int) -> tuple[bytes, dict]:
        index = self.catalogs()
        hit = index.lookup(record.sha1)
        if hit is None:
            raise AssetError(
                f"sha1 {record.sha1.hex()} ({record.name}) is not in any cas.cat "
                f"({index.total_entries} unique chunks searched)"
            )
        if hit["kind"] == "patch":
            if depth > 4:
                raise AssetError("patch chain is nested more than 4 levels deep")
            entry = hit["entry"]
            base_hit = index.lookup(entry.base_id)
            delta_hit = index.lookup(entry.delta_id)
            if base_hit is None or delta_hit is None:
                raise AssetError(
                    f"patch chunk {record.sha1.hex()} is missing its "
                    f"{'base' if base_hit is None else 'delta'} chunk"
                )
            if base_hit["kind"] != "normal" or delta_hit["kind"] != "normal":
                raise AssetError(
                    f"patch chunk {record.sha1.hex()} has a non-normal "
                    f"base/delta variant ({base_hit['kind']}/{delta_hit['kind']})"
                )
            base_raw = base_hit["catalog"].read_chunk(base_hit["entry"])
            delta_raw = delta_hit["catalog"].read_chunk(delta_hit["entry"])
            data = patch.apply(base_raw, delta_raw)
            location = {
                "kind": "patch-delta",
                "cas": delta_hit["cas"],
                "offset": delta_hit["offset"],
                "size": delta_hit["size"],
                "catalog": delta_hit["catalog"].path,
                "base": base_hit["catalog"].cas_path(base_hit["entry"].data_index),
                "base_offset": base_hit["offset"],
                "blocks": [],
            }
            if record.original_size and len(data) != record.original_size:
                raise AssetError(
                    f"patched chunk produced {len(data)} bytes, .sb says "
                    f"originalSize={record.original_size}"
                )
            return data, location

        if hit["kind"] == "encrypted":
            raise AssetError(
                f"chunk {record.sha1.hex()} is encrypted with key id "
                f"{hit.get('key_id')!r}; the key lives in initfs_Win32/Scripts/CasEncrypt.yaml "
                f"and is not implemented here"
            )
        raw = hit["catalog"].read_chunk(hit["entry"])
        location = {
            "kind": "normal",
            "cas": hit["cas"],
            "offset": hit["offset"],
            "size": hit["size"],
            "catalog": hit["catalog"].path,
        }
        if record.original_size and record.original_size != len(raw):
            blocks = compress.describe_blocks(raw)
            location["blocks"] = blocks
            data = compress.decompress(raw, record.original_size)
        else:
            data = raw
            location["blocks"] = []
        return data, location

    def partition(self, record: AssetRecord) -> partition.Partition:
        data, location = self.chunk_data(record)
        try:
            part = partition.Partition(data)
        except partition.PartitionError as exc:
            raise AssetError(
                f"{record.name}: chunk at {location['cas'].name}+0x{location['offset']:X} "
                f"({len(data)} bytes decompressed) is not an EBX partition: {exc}"
            ) from exc
        part.location = location
        return part
