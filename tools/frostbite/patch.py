"""Frostbite patch-delta chunks (``PatchEntry``: base + delta -> content).

``PatchEntry`` in ``cas.cat`` says "this chunk's content = base + delta".  Both
the base and the delta are *compressed block streams* (the same format
:mod:`frostbite.compress` reads); the delta additionally interleaves 4-byte
big-endian control words::

    control = uint32 big-endian
    type    = control >> 28          (0 Copy, 1 CompressedChange,
                                      2 UncompressedChange, 3 Add, 4 Remove)
    count   = control & 0x0FFFFFFF

Ported from Gibbed's ``PatchHelper.cs``.  The output is fully decompressed data
(the base's blocks are decompressed as they are copied), so a patched chunk does
not need another pass through :func:`frostbite.compress.decompress`.
"""
from __future__ import annotations

import struct

from . import compress

__all__ = ["PatchError", "PT_COPY", "PT_COMPRESSED_CHANGE", "PT_UNCOMPRESSED_CHANGE",
           "PT_ADD", "PT_REMOVE", "apply"]

PT_COPY = 0
PT_COMPRESSED_CHANGE = 1
PT_UNCOMPRESSED_CHANGE = 2
PT_ADD = 3
PT_REMOVE = 4


class PatchError(Exception):
    pass


class _Cursor:
    """A byte cursor that can also pull Frostbite compressed blocks."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    @property
    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise PatchError(f"delta truncated: wanted {n} bytes at 0x{self.pos:X}")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

    def block(self) -> bytes:
        header = compress.read_block_header(self.data, self.pos)
        end = self.pos + 8 + header.compressed_size
        if end > len(self.data):
            raise PatchError(f"block at 0x{self.pos:X} runs past end of stream")
        body = self.data[self.pos + 8:end]
        self.pos = end
        if header.compression_type == compress.TYPE_NONE:
            if header.compressed_size != header.uncompressed_size:
                raise PatchError(f"bad uncompressed block {header!r}")
            return body
        if header.compression_type == compress.TYPE_ZSTD:
            out = compress._load_zstd()[0](body, header.uncompressed_size)
            if header.uncompressed_size and len(out) != header.uncompressed_size:
                raise PatchError(f"zstd block produced {len(out)} bytes, "
                                 f"header said {header.uncompressed_size}")
            return out
        if header.compression_type == compress.TYPE_ZLIB:
            import zlib
            return zlib.decompress(body)
        raise PatchError(f"unsupported block compression {header!r}")

    def skip_block(self) -> None:
        header = compress.read_block_header(self.data, self.pos)
        self.pos += 8 + header.compressed_size


def apply(base: bytes, delta: bytes) -> bytes:
    """Apply ``delta`` to ``base`` (both raw compressed block streams)."""
    inp = _Cursor(base)
    dlt = _Cursor(delta)
    out = bytearray()

    while not dlt.eof:
        control = dlt.u32()
        count = control & 0x0FFFFFFF
        patch_type = control >> 28

        if patch_type == PT_COPY:
            for _ in range(count):
                out += inp.block()

        elif patch_type == PT_COMPRESSED_CHANGE:
            input_bytes = inp.block()
            o = 0
            for _ in range(count):
                input_offset = dlt.u16()
                input_skip = dlt.u16()
                copy_length = input_offset - o
                if copy_length < 0 or o + copy_length > len(input_bytes):
                    raise PatchError("compressed-change copy runs past the base block")
                out += input_bytes[o:o + copy_length]
                out += dlt.block()
                o = input_offset + input_skip
            out += input_bytes[o:]

        elif patch_type == PT_UNCOMPRESSED_CHANGE:
            input_bytes = inp.block()
            total_size = 1 + dlt.u16()
            start = len(out)
            chunk = _Cursor(dlt.take(count))
            o = 0
            while not chunk.eof:
                input_offset = chunk.u16()
                input_skip = chunk.u8()
                delta_copy = chunk.u8()
                copy_length = input_offset - o
                if copy_length < 0 or o + copy_length > len(input_bytes):
                    raise PatchError("uncompressed-change copy runs past the base block")
                out += input_bytes[o:o + copy_length]
                if delta_copy:
                    out += chunk.take(delta_copy)
                o = input_offset + input_skip
            out += input_bytes[o:]
            if len(out) - start != total_size:
                raise PatchError(
                    f"uncompressed-change produced {len(out) - start} bytes, "
                    f"declared {total_size}"
                )

        elif patch_type == PT_ADD:
            for _ in range(count):
                out += dlt.block()

        elif patch_type == PT_REMOVE:
            for _ in range(count):
                inp.skip_block()

        else:
            raise PatchError(f"unknown patch type {patch_type}")

    if not inp.eof:
        # trailing base data is not an error in the game, but note it
        out += b""
    return bytes(out)
