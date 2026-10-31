"""Frostbite chunk compression (the per-block wrapper inside ``.cas`` data).

Every *compressed* chunk (EBX, res, chunk) is a sequence of blocks::

    int32  uncompressedBlockSize   big-endian
    uint32 flags                   big-endian
        bits 24..31  compression type   (0 = none, 2 = zlib, 15 = zstd)
        bits 20..23  compression flags  (which of zlib/lz4/zstd are legal)
        bits  0..19  compressedBlockSize

Blocks are concatenated until ``originalSize`` bytes have been produced.  This
matches Gibbed's ``CompressionHeader.cs`` / ``CompressionHelper.cs`` and was
confirmed against real MEA chunks: for the asset used in the docs the chunk is
834 bytes of cas data that expands to 1376 bytes.

zstd is decoded with the Python 3.14 standard library module
``compression.zstd`` (PEP 784).  If that is unavailable we fall back to
``ctypes`` against the ``libzstd`` DLL that ships with the Frosty editor.
"""
from __future__ import annotations

import ctypes
import struct
import zlib
from pathlib import Path

__all__ = [
    "CompressionError",
    "TYPE_NONE",
    "TYPE_ZLIB",
    "TYPE_ZSTD",
    "BlockHeader",
    "read_block_header",
    "decompress",
    "describe_blocks",
]

TYPE_NONE = 0
TYPE_ZLIB = 2
TYPE_ZSTD = 15

_TYPE_NAMES = {
    0: "none",
    1: "lz77?",
    2: "zlib",
    3: "lz4?",
    4: "lz4?",
    5: "lz4?",
    6: "lz4?",
    7: "lz4?",
    8: "lz4?",
    9: "unknown9",
    15: "zstd",
}

_THIRDPARTY = Path(
    r"C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld"
    r"\Mass Effect Andromeda Mods\FrostyEditor\ThirdParty"
)

_zstd_api = None
_zstd_error = None


class CompressionError(Exception):
    """Raised when a chunk cannot be decompressed."""


class BlockHeader:
    __slots__ = ("uncompressed_size", "raw_flags", "compression_type",
                 "compression_flags", "compressed_size", "offset")

    def __init__(self, offset, uncompressed_size, raw_flags):
        self.offset = offset
        self.uncompressed_size = uncompressed_size
        self.raw_flags = raw_flags
        self.compression_type = (raw_flags >> 24) & 0xFF
        self.compression_flags = (raw_flags >> 20) & 0xF
        self.compressed_size = raw_flags & 0xFFFFF

    @property
    def type_name(self) -> str:
        return _TYPE_NAMES.get(self.compression_type, f"type{self.compression_type}")

    def __repr__(self):
        return (
            f"BlockHeader(@0x{self.offset:X} {self.type_name} "
            f"compressed={self.compressed_size} uncompressed={self.uncompressed_size} "
            f"flags=0x{self.compression_flags:X})"
        )


def read_block_header(data: bytes, offset: int) -> BlockHeader:
    if offset + 8 > len(data):
        raise CompressionError(f"truncated block header at 0x{offset:X}")
    uncompressed, flags = struct.unpack_from(">iI", data, offset)
    return BlockHeader(offset, uncompressed, flags)


# ---------------------------------------------------------------------------
# zstd backends
# ---------------------------------------------------------------------------
def _load_zstd():
    """Return (decompress_fn, backend_name)."""
    global _zstd_api, _zstd_error
    if _zstd_api is not None:
        return _zstd_api
    # 1) CPython 3.14 stdlib
    try:
        from compression import zstd as std_zstd  # type: ignore

        def _stdlib(data: bytes, expected: int) -> bytes:
            out = std_zstd.decompress(data)
            if expected and len(out) != expected:
                raise CompressionError(
                    f"zstd produced {len(out)} bytes, header promised {expected}"
                )
            return out

        _zstd_api = (_stdlib, f"compression.zstd (stdlib, zstd {std_zstd.zstd_version})")
        return _zstd_api
    except Exception as exc:  # pragma: no cover - only on non-3.14
        _zstd_error = f"compression.zstd unavailable: {exc}"

    # 2) ctypes against the Frosty-editor DLL
    for name in ("libzstd.1.3.4.dll", "libzstd.1.2.0.dll", "libzstd.1.1.5.dll"):
        dll = _THIRDPARTY / name
        if not dll.is_file():
            continue
        try:
            lib = ctypes.CDLL(str(dll))
        except OSError as exc:  # pragma: no cover
            _zstd_error = f"{name}: {exc}"
            continue
        lib.ZSTD_decompress.restype = ctypes.c_size_t
        lib.ZSTD_decompress.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t
        ]
        lib.ZSTD_isError.restype = ctypes.c_uint
        lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        lib.ZSTD_decompressBound.restype = ctypes.c_ulonglong
        lib.ZSTD_decompressBound.argtypes = [ctypes.c_void_p, ctypes.c_size_t]

        def _ctypes_decompress(data: bytes, expected: int, _lib=lib, _name=name) -> bytes:
            bound = int(_lib.ZSTD_decompressBound(data, len(data)))
            if bound <= 0:
                bound = max(expected, len(data) * 64, 1 << 20)
            out = ctypes.create_string_buffer(bound)
            got = _lib.ZSTD_decompress(out, bound, data, len(data))
            if _lib.ZSTD_isError(got):
                raise CompressionError(f"{_name}: ZSTD_decompress failed (code {got})")
            return out.raw[:got]

        _zstd_api = (_ctypes_decompress, f"ctypes {name}")
        return _zstd_api

    raise CompressionError(
        "no zstd backend available (" + (_zstd_error or "compression.zstd missing") + ")"
    )


def zstd_backend_name() -> str:
    return _load_zstd()[1]


# ---------------------------------------------------------------------------
def describe_blocks(data: bytes) -> list[BlockHeader]:
    """Walk the block chain without decompressing (used by ``selftest``)."""
    headers = []
    offset = 0
    while offset + 8 <= len(data):
        header = read_block_header(data, offset)
        headers.append(header)
        if header.compressed_size == 0:
            break
        offset += 8 + header.compressed_size
        if header.uncompressed_size == 0:
            break
    return headers


def decompress(data: bytes, original_size: int = 0) -> bytes:
    """Decompress a Frostbite chunk.

    ``original_size`` (from the ``.sb`` record) is required: the block chain has
    no terminator, so we stop once that many bytes have been produced.
    """
    if original_size <= 0:
        raise CompressionError("original_size is required to decompress a chunk")

    out = bytearray()
    offset = 0
    zstd = None
    while len(out) < original_size:
        if offset >= len(data):
            raise CompressionError(
                f"ran out of input after {len(out)}/{original_size} bytes"
            )
        header = read_block_header(data, offset)
        if header.compressed_size == 0 or offset + 8 + header.compressed_size > len(data):
            raise CompressionError(
                f"block at 0x{offset:X} declares {header.compressed_size} bytes but only "
                f"{len(data) - offset - 8} remain ({header!r})"
            )
        body = data[offset + 8:offset + 8 + header.compressed_size]

        if header.compression_type == TYPE_NONE:
            if header.compressed_size != header.uncompressed_size:
                raise CompressionError(
                    f"uncompressed block at 0x{offset:X} has mismatched sizes {header!r}"
                )
            out += body
        elif header.compression_type == TYPE_ZSTD:
            if zstd is None:
                zstd = _load_zstd()
            out += zstd[0](body, header.uncompressed_size)
        elif header.compression_type == TYPE_ZLIB:
            out += zlib.decompress(body)
        else:
            raise CompressionError(
                f"unsupported compression {header!r} at 0x{offset:X}"
            )

        offset += 8 + header.compressed_size

    if len(out) != original_size:
        raise CompressionError(
            f"decompressed {len(out)} bytes, expected {original_size}"
        )
    return bytes(out)
