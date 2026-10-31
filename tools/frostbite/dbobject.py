"""Reader for Frostbite "DbObject" streams.

This is the generic tagged-value container used by ``.sb`` (superbundle),
``.toc`` (table of contents) and ``layout.toc`` files.  The format was
confirmed byte-for-byte against the real Mass Effect Andromeda files and
against Gibbed's ``Gibbed.Frostbite3.Common/DbObject/Serializer.cs``.

Stream shape
------------
A stream is a single value.  Every value starts with a one-byte *tag*::

    tag & 0x1F  -> ValueType
    tag >> 5    -> ValueFlags (unused here)

Containers (Object / Array) are length-prefixed with a 7-bit little-endian
"packed" varint covering everything after the varint itself::

    Object : varint length, then repeated (tag, name C-string, value)
             terminated by a tag with ValueType.Invalid (0)
    Array  : varint length, then repeated (tag, value)
             terminated by a tag with ValueType.Invalid (0)

Primitive encodings (all little-endian unless stated)::

    Bool    1 byte, != 0
    String  varint length, then UTF-8 C-string (the NUL is inside the length)
    Int32   4 bytes
    Int64   8 bytes
    Float64 8 bytes
    Guid    16 bytes, *big-endian* field order (Gibbed: ReadValueGuid(Endian.Big))
    SHA1    20 raw bytes
    Bytes   varint length, then that many bytes

Verified example (``Data/Win32/anchorchannels.sb``, first 4 bytes)::

    82          tag: Object, flags=4
    C6 35       packed varint 0x1A86 = 6790 ... actually 70 | (53 << 7) = 6854
    01          tag: Array  (property "bundles")
    "bundles\\0"
    ...
"""
from __future__ import annotations

import struct

__all__ = [
    "DbObjectError",
    "ValueType",
    "Guid",
    "Reader",
    "parse",
]


class DbObjectError(Exception):
    """Raised when a DbObject stream does not match the expected layout."""


class ValueType:
    Invalid = 0
    Array = 1
    Object = 2
    Bool = 6
    String = 7
    Int32 = 8
    Int64 = 9
    Float64 = 12
    Guid = 15
    SHA1 = 16
    Bytes = 19


_NAME = {
    ValueType.Invalid: "Invalid",
    ValueType.Array: "Array",
    ValueType.Object: "Object",
    ValueType.Bool: "Bool",
    ValueType.String: "String",
    ValueType.Int32: "Int32",
    ValueType.Int64: "Int64",
    ValueType.Float64: "Float64",
    ValueType.Guid: "Guid",
    ValueType.SHA1: "SHA1",
    ValueType.Bytes: "Bytes",
}


class Guid:
    """A 16-byte Frostbite GUID plus its .NET text rendering.

    ``raw`` is the 16 bytes in the order .NET's ``Guid.ToByteArray()`` would
    produce (data1/data2/data3 little-endian, data4 verbatim).  That is the
    order a save file uses, so it is the form to compare against.

    ``Reader`` builds these from *big-endian* field order (the DbObject encoding).
    """

    __slots__ = ("raw",)

    def __init__(self, raw: bytes):
        if len(raw) != 16:
            raise ValueError("guid must be 16 bytes")
        self.raw = bytes(raw)

    @classmethod
    def from_be_fields(cls, data: bytes) -> "Guid":
        """Build from 16 bytes stored with big-endian data1/data2/data3."""
        return cls(
            data[0:4][::-1] + data[4:6][::-1] + data[6:8][::-1] + data[8:16]
        )

    @classmethod
    def from_le_fields(cls, data: bytes) -> "Guid":
        """Build from 16 bytes already in .NET raw order (little-endian fields)."""
        return cls(data)

    @classmethod
    def from_text(cls, text: str) -> "Guid":
        parts = text.strip().strip("{}").split("-")
        if len(parts) != 5:
            raise ValueError(f"not a GUID: {text!r}")
        return cls(
            bytes.fromhex(parts[0])[::-1]
            + bytes.fromhex(parts[1])[::-1]
            + bytes.fromhex(parts[2])[::-1]
            + bytes.fromhex(parts[3])
            + bytes.fromhex(parts[4])
        )

    @property
    def text(self) -> str:
        r = self.raw
        a = int.from_bytes(r[0:4], "little")
        b = int.from_bytes(r[4:6], "little")
        c = int.from_bytes(r[6:8], "little")
        return f"{a:08x}-{b:04x}-{c:04x}-{r[8:10].hex()}-{r[10:16].hex()}"

    @property
    def hex(self) -> str:
        return self.raw.hex()

    def __eq__(self, other):
        return isinstance(other, Guid) and other.raw == self.raw

    def __hash__(self):
        return hash(self.raw)

    def __repr__(self):
        return f"Guid({self.text})"

    def __str__(self):
        return self.text


class Reader:
    """Cursor over a bytes object holding a DbObject stream."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    # -- primitives ---------------------------------------------------------
    def need(self, n: int) -> None:
        if self.pos + n > len(self.data):
            raise DbObjectError(
                f"truncated stream: want {n} byte(s) at 0x{self.pos:X}, "
                f"only {len(self.data) - self.pos} left"
            )

    def u8(self) -> int:
        self.need(1)
        v = self.data[self.pos]
        self.pos += 1
        return v

    def take(self, n: int) -> bytes:
        self.need(n)
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v

    def packed_uint(self) -> int:
        """7-bit little-endian varint (Gibbed: ReadPackedValueUInt32)."""
        value = 0
        shift = 0
        while True:
            b = self.u8()
            value |= (b & 0x7F) << shift
            if not b & 0x80:
                return value
            shift += 7
            if shift > 35:
                raise DbObjectError("packed varint too long")

    def cstring(self, encoding: str = "utf-8") -> str:
        end = self.data.find(b"\x00", self.pos)
        if end < 0:
            raise DbObjectError(f"unterminated string at 0x{self.pos:X}")
        raw = self.data[self.pos:end]
        self.pos = end + 1
        return raw.decode(encoding, "replace")

    # -- values -------------------------------------------------------------
    def value(self, tag_type: int):
        if tag_type == ValueType.Bool:
            return self.u8() != 0
        if tag_type == ValueType.String:
            length = self.packed_uint()
            start = self.pos
            end = start + length
            if end > len(self.data):
                raise DbObjectError("string runs past end of stream")
            # the recorded length includes the trailing NUL
            body = self.data[start:end]
            self.pos = end
            return body.split(b"\x00", 1)[0].decode("utf-8", "replace")
        if tag_type == ValueType.Int32:
            self.need(4)
            v = struct.unpack_from("<i", self.data, self.pos)[0]
            self.pos += 4
            return v
        if tag_type == ValueType.Int64:
            self.need(8)
            v = struct.unpack_from("<q", self.data, self.pos)[0]
            self.pos += 8
            return v
        if tag_type == ValueType.Float64:
            self.need(8)
            v = struct.unpack_from("<d", self.data, self.pos)[0]
            self.pos += 8
            return v
        if tag_type == ValueType.Guid:
            return Guid.from_be_fields(self.take(16))
        if tag_type == ValueType.SHA1:
            return self.take(20)
        if tag_type == ValueType.Bytes:
            length = self.packed_uint()
            return self.take(length)
        if tag_type == ValueType.Array:
            return self.array()
        if tag_type == ValueType.Object:
            return self.object()
        raise DbObjectError(
            f"unsupported ValueType {tag_type} at 0x{self.pos - 1:X}"
        )

    def array(self) -> list:
        length = self.packed_uint()
        end = self.pos + length
        if end > len(self.data):
            raise DbObjectError("array runs past end of stream")
        out = []
        while True:
            tag = self.u8()
            if (tag & 0x1F) == ValueType.Invalid:
                break
            out.append(self.value(tag & 0x1F))
        if self.pos != end:
            raise DbObjectError(
                f"array ended at 0x{self.pos:X}, declared 0x{end:X}"
            )
        return out

    def object(self) -> dict:
        length = self.packed_uint()
        end = self.pos + length
        if end > len(self.data):
            raise DbObjectError("object runs past end of stream")
        out = {}
        while True:
            tag = self.u8()
            if (tag & 0x1F) == ValueType.Invalid:
                break
            name = self.cstring()
            out[name] = self.value(tag & 0x1F)
        if self.pos != end:
            raise DbObjectError(
                f"object ended at 0x{self.pos:X}, declared 0x{end:X}"
            )
        return out


def parse(data: bytes) -> dict:
    """Parse a whole DbObject stream (everything after any file layer)."""
    r = Reader(data)
    tag = r.u8()
    value = r.value(tag & 0x1F)
    if r.pos != len(data):
        raise DbObjectError(
            f"{len(data) - r.pos} trailing byte(s) after root object"
        )
    return value
