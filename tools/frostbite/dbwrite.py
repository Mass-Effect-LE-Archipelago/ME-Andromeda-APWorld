"""Typed DbObject reader/writer, to prove we can re-emit a `.fbmod` byte for byte.

The existing parser discards value types, so it cannot write. This module keeps the tag byte for
every value and re-encodes it exactly, which is the prerequisite for authoring mods.
"""
from __future__ import annotations

import struct

from .dbobject import DbObjectError, ValueType


class TypedReader:
    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def u8(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, n: int) -> bytes:
        out = self.data[self.pos:self.pos + n]
        if len(out) != n:
            raise DbObjectError("unexpected end of data")
        self.pos += n
        return out

    def packed(self) -> int:
        value = shift = 0
        while True:
            b = self.u8()
            value |= (b & 0x7F) << shift
            if not b & 0x80:
                return value
            shift += 7

    def cstring(self) -> str:
        end = self.data.find(b"\x00", self.pos)
        raw = self.data[self.pos:end]
        self.pos = end + 1
        return raw.decode("utf-8", "replace")

    def value(self, tag: int):
        """Return (raw tag, value): the raw byte keeps flags above 0x1F (e.g. 0x80)."""
        t = tag & 0x1F
        if t == ValueType.Bool:
            return tag, self.u8() != 0
        if t == ValueType.String:
            length = self.packed()
            body = self.take(length)
            return tag, body[:-1].decode("utf-8", "replace")
        if t == ValueType.Int32:
            return tag, struct.unpack_from("<i", self.take(4))[0]
        if t == ValueType.Int64:
            return tag, struct.unpack_from("<q", self.take(8))[0]
        if t == ValueType.Float64:
            return tag, struct.unpack_from("<d", self.take(8))[0]
        if t == ValueType.Guid:
            return tag, self.take(16)
        if t == ValueType.SHA1:
            return tag, self.take(20)
        if t == ValueType.Bytes:
            return tag, self.take(self.packed())
        if t == ValueType.Array:
            return tag, self.array()
        if t == ValueType.Object:
            return tag, self.object()
        raise DbObjectError(f"unsupported type {tag} at 0x{self.pos - 1:X}")

    def array(self) -> list:
        # read the length FIRST: `self.pos + self.packed()` would evaluate pos before the varint
        # advances it, which silently shifts the frame by the length of the varint
        length = self.packed()
        end = self.pos + length
        out = []
        while True:
            tag = self.u8()
            if (tag & 0x1F) == ValueType.Invalid:
                break
            out.append(self.value(tag))
        if self.pos != end:
            raise DbObjectError(f"array ended 0x{self.pos:X} != 0x{end:X}")
        return out

    def object(self) -> list:
        length = self.packed()
        end = self.pos + length
        out = []
        while True:
            tag = self.u8()
            if (tag & 0x1F) == ValueType.Invalid:
                break
            name = self.cstring()
            out.append((name, self.value(tag)))
        if self.pos != end:
            raise DbObjectError(f"object ended 0x{self.pos:X} != 0x{end:X}")
        return out


def packed(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def write_value(tag: int, value) -> bytes:
    t = tag & 0x1F
    if t == ValueType.Bool:
        return bytes([1 if value else 0])
    if t == ValueType.String:
        body = value.encode("utf-8") + b"\x00"
        return packed(len(body)) + body
    if t == ValueType.Int32:
        return struct.pack("<i", value)
    if t == ValueType.Int64:
        return struct.pack("<q", value)
    if t == ValueType.Float64:
        return struct.pack("<d", value)
    if t in (ValueType.Guid, ValueType.SHA1, ValueType.Bytes):
        if t == ValueType.Bytes:
            return packed(len(value)) + value
        return value
    if t == ValueType.Array:
        body = b"".join(bytes([child_tag]) + write_value(child_tag, child) for child_tag, child in value)
        return packed(len(body) + 1) + body + b"\x00"
    if t == ValueType.Object:
        body = b"".join(bytes([child_tag]) + name.encode("utf-8") + b"\x00" + write_value(child_tag, child)
                        for name, (child_tag, child) in value)
        return packed(len(body) + 1) + body + b"\x00"
    raise DbObjectError(f"cannot write type {tag}")


def write_root(tag: int, value) -> bytes:
    return bytes([tag]) + write_value(tag, value)
