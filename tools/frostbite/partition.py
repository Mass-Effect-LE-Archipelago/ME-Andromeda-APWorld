"""EBX "partition" reader (the payload of a decompressed ``.cas`` chunk).

Layout confirmed against Gibbed's ``PartitionFile.cs`` and against the real
files: every EBX chunk in this install starts with ``CE D1 B2 0F``
(= 0x0FB2D1CE little-endian) and its header is self-checking, because

    headerSize == 64 + imports*32 + nameTableSize + fields*16 + types*16
                 + align(instances*4, 16) + align(arrays*12, 16)

so a misparse announces itself immediately instead of producing plausible junk.

Header (little-endian for MEA)::

     0  uint32 magic            0x0FB2D1CE
     4  uint32 headerSize
     8  uint32 dataSize
    12  uint32 importCount
    16  uint16 instanceCount
    18  uint16 namedInstanceCount
    20  uint16 exportedInstanceCount
    22  uint16 typeDefinitionCount
    24  uint16 fieldDefinitionCount
    26  uint16 nameTableSize
    28  uint32 stringTableSize
    32  uint32 arrayCount
    36  uint32 arrayOffset
    40  Guid   this partition's own GUID   <-- the "asset GUID"
    56  byte[8] padding/unused

Then imports (32 bytes each: partition GUID + instance GUID), the name table
(NUL-separated UTF-8), field definitions (16 bytes), type definitions
(16 bytes), instances (4 bytes each + 16-byte alignment), arrays (12 bytes each
+ alignment) and finally the data blob.

The data blob starts with the string table (``stringTableSize`` bytes); struct
instances follow, each optionally prefixed by a 16-byte instance GUID when its
*definition index* is below ``namedInstanceCount``.

All GUIDs inside a partition are stored in .NET "raw" byte order (data1/2/3
little-endian).  :class:`~frostbite.dbobject.Guid` normalises both orders.
"""
from __future__ import annotations

import struct

from .dbobject import Guid

__all__ = [
    "PartitionError",
    "MAGIC",
    "NAME_HASH",
    "FieldDef",
    "TypeDef",
    "Instance",
    "Partition",
    "djb",
]

MAGIC = 0x0FB2D1CE

# DataType enum (DefinitionFlags.DataType = (raw >> 4) & 0x1F)
DT_VOID = 0
DT_DBOBJECT = 1
DT_VALUE = 2
DT_CLASS = 3
DT_LIST = 4
DT_ARRAY = 5
DT_STRING = 6
DT_STRING2 = 7
DT_ENUM = 8
DT_FILE = 9
DT_BOOLEAN = 10
DT_INT8 = 11
DT_UINT8 = 12
DT_INT16 = 13
DT_UINT16 = 14
DT_INT32 = 15
DT_UINT32 = 16
DT_INT64 = 17
DT_UINT64 = 18
DT_FLOAT32 = 19
DT_FLOAT64 = 20
DT_GUID = 21
DT_SHA1 = 22

_DT_NAMES = {
    0: "Void", 1: "DbObject", 2: "Value", 3: "Class", 4: "List", 5: "Array",
    6: "String", 7: "String2", 8: "Enum", 9: "File", 10: "Boolean", 11: "Int8",
    12: "UInt8", 13: "Int16", 14: "UInt16", 15: "Int32", 16: "UInt32",
    17: "Int64", 18: "UInt64", 19: "Float32", 20: "Float64", 21: "Guid",
    22: "SHA1",
}

_FIXED_SIZE = {
    DT_BOOLEAN: 1, DT_INT8: 1, DT_UINT8: 1,
    DT_INT16: 2, DT_UINT16: 2,
    DT_INT32: 4, DT_UINT32: 4, DT_FLOAT32: 4,
    DT_INT64: 8, DT_UINT64: 8, DT_FLOAT64: 8,
    DT_GUID: 16, DT_SHA1: 20,
    DT_STRING2: 4, DT_CLASS: 4, DT_LIST: 4, DT_ENUM: 4,
}


class PartitionError(Exception):
    pass


def djb(text: str) -> int:
    """Gibbed's DJB hash, used for every name in a partition."""
    h = 5381
    for ch in text:
        h = (h * 33) & 0xFFFFFFFF
        h ^= ord(ch) & 0xFF
    return h


class FieldDef:
    __slots__ = ("name_hash", "flags_raw", "type_index", "data_offset", "unknown0c", "name")

    def __init__(self, name_hash, flags_raw, type_index, data_offset, unknown0c):
        self.name_hash = name_hash
        self.flags_raw = flags_raw
        self.type_index = type_index
        self.data_offset = data_offset
        self.unknown0c = unknown0c
        self.name = None

    @property
    def data_type(self) -> int:
        return (self.flags_raw >> 4) & 0x1F

    @property
    def data_kind(self) -> int:
        return (self.flags_raw >> 2) & 0x3

    @property
    def data_flags(self) -> int:
        return (self.flags_raw >> 11) & 0x1F

    @property
    def type_name(self) -> str:
        return _DT_NAMES.get(self.data_type, f"type{self.data_type}")

    @property
    def label(self) -> str:
        return self.name or f"#{self.name_hash:08X}"

    def __repr__(self):
        return f"FieldDef({self.label} {self.type_name} type={self.type_index} @+{self.data_offset})"


class TypeDef:
    __slots__ = (
        "name_hash", "field_start", "field_count", "alignment", "flags_raw",
        "data_size", "unknown0e", "name",
    )

    def __init__(self, name_hash, field_start, field_count, alignment, flags_raw,
                 data_size, unknown0e):
        self.name_hash = name_hash
        self.field_start = field_start
        self.field_count = field_count
        self.alignment = alignment
        self.flags_raw = flags_raw
        self.data_size = data_size
        self.unknown0e = unknown0e
        self.name = None

    @property
    def data_type(self) -> int:
        return (self.flags_raw >> 4) & 0x1F

    @property
    def label(self) -> str:
        return self.name or f"#{self.name_hash:08X}"

    def __repr__(self):
        return f"TypeDef({self.label} fields={self.field_count} size={self.data_size})"


class Instance:
    __slots__ = ("entry_index", "index", "type_index", "guid", "data_offset")

    def __init__(self, entry_index, index, type_index, guid, data_offset):
        self.entry_index = entry_index
        self.index = index
        self.type_index = type_index
        self.guid = guid          # bytes or None
        self.data_offset = data_offset

    def __repr__(self):
        g = self.guid.hex() if self.guid else "-"
        return f"Instance(#{self.index} type={self.type_index} guid={g} @+{self.data_offset})"


def _align(value: int, alignment: int) -> int:
    if alignment <= 1:
        return value
    rem = value % alignment
    return value if rem == 0 else value + (alignment - rem)


class Partition:
    """A parsed EBX partition."""

    def __init__(self, data: bytes):
        self.buffer = data
        self.endian = "<"
        self.guid: Guid | None = None
        self.imports: list[tuple[Guid, Guid]] = []
        self.names: list[str] = []
        self.fields: list[FieldDef] = []
        self.types: list[TypeDef] = []
        self.instance_entries: list[tuple[int, int]] = []
        self.arrays: list[tuple[int, int, int]] = []
        self.named_instance_count = 0
        self.exported_instance_count = 0
        self.string_table_size = 0
        self.array_offset = 0
        self.header_size = 0
        self.data_size = 0
        self.data = b""
        self.instances: list[Instance] = []
        self._parse()

    # -- header -------------------------------------------------------------
    def _parse(self) -> None:
        data = self.buffer
        if len(data) < 64:
            raise PartitionError(f"partition too small ({len(data)} bytes)")
        magic_le = struct.unpack_from("<I", data, 0)[0]
        if magic_le == MAGIC:
            self.endian = "<"
        elif struct.unpack_from(">I", data, 0)[0] == MAGIC:
            self.endian = ">"
        else:
            raise PartitionError(
                f"bad partition magic {data[:4].hex(' ')} "
                f"(want CE D1 B2 0F for little-endian)"
            )
        e = self.endian
        (self.header_size, self.data_size, import_count) = struct.unpack_from(e + "III", data, 4)
        (instance_count, self.named_instance_count, self.exported_instance_count,
         type_count, field_count, name_table_size) = struct.unpack_from(e + "HHHHHH", data, 16)
        (self.string_table_size, array_count, self.array_offset) = struct.unpack_from(e + "III", data, 28)
        raw = data[40:56]
        self.guid = Guid.from_le_fields(raw) if e == "<" else Guid.from_be_fields(raw)

        computed = (
            64
            + import_count * 32
            + name_table_size
            + field_count * 16
            + type_count * 16
            + _align(instance_count * 4, 16)
            + _align(array_count * 12, 16)
        )
        if computed != self.header_size:
            raise PartitionError(
                f"header size mismatch: declared {self.header_size}, computed {computed} "
                f"(imports={import_count} names={name_table_size} fields={field_count} "
                f"types={type_count} instances={instance_count} arrays={array_count})"
            )
        if self.header_size + self.data_size != len(data):
            raise PartitionError(
                f"header+data = {self.header_size + self.data_size}, chunk is {len(data)}"
            )

        pos = 64
        for _ in range(import_count):
            a = data[pos:pos + 16]
            b = data[pos + 16:pos + 32]
            if e == "<":
                self.imports.append((Guid.from_le_fields(a), Guid.from_le_fields(b)))
            else:
                self.imports.append((Guid.from_be_fields(a), Guid.from_be_fields(b)))
            pos += 32

        name_bytes = data[pos:pos + name_table_size]
        pos += name_table_size
        self.names = [s.decode("utf-8", "replace") for s in name_bytes.split(b"\x00") if s]

        hash_to_name = {}
        for name in self.names:
            hash_to_name.setdefault(djb(name), name)

        for _ in range(field_count):
            name_hash, flags_raw, type_index, data_offset, unknown0c = struct.unpack_from(
                e + "IHHII", data, pos
            )
            f = FieldDef(name_hash, flags_raw, type_index, data_offset, unknown0c)
            f.name = hash_to_name.get(name_hash)
            self.fields.append(f)
            pos += 16

        for _ in range(type_count):
            name_hash, field_start, field_count_, alignment, flags_raw, data_size, unknown0e = (
                struct.unpack_from(e + "IiBBHHH", data, pos)
            )
            t = TypeDef(name_hash, field_start, field_count_, alignment, flags_raw,
                        data_size, unknown0e)
            t.name = hash_to_name.get(name_hash)
            self.types.append(t)
            pos += 16

        for _ in range(instance_count):
            type_index, count = struct.unpack_from(e + "HH", data, pos)
            self.instance_entries.append((type_index, count))
            pos += 4
        pos += _align(instance_count * 4, 16) - instance_count * 4

        for _ in range(array_count):
            data_offset, item_count, type_index = struct.unpack_from(e + "IiI", data, pos)
            self.arrays.append((data_offset, item_count, type_index))
            pos += 12
        pos += _align(array_count * 12, 16) - array_count * 12

        if pos != self.header_size:
            raise PartitionError(f"header ended at {pos}, expected {self.header_size}")

        self.data = data[self.header_size:self.header_size + self.data_size]
        self._build_instances()

    # -- instances ----------------------------------------------------------
    def _build_instances(self) -> None:
        offset = self.string_table_size
        index = 0
        for entry_index, (type_index, count) in enumerate(self.instance_entries):
            type_def = self.types[type_index]
            if type_def.alignment == 4:
                type_size = _align(type_def.data_size - 8, type_def.alignment)
            else:
                type_size = _align(type_def.data_size, type_def.alignment)
            for _ in range(count):
                offset = _align(offset, type_def.alignment)
                guid = None
                if entry_index < self.named_instance_count:
                    guid = self.data[offset:offset + 16]
                    offset += 16
                instance_offset = offset
                if type_def.alignment == 4:
                    instance_offset -= 8
                self.instances.append(
                    Instance(entry_index, index, type_index, guid, instance_offset)
                )
                index += 1
                offset += type_size

    # -- value reading ------------------------------------------------------
    def struct(self, type_index: int, base: int, depth: int = 0, seen: frozenset | None = None) -> dict:
        """Read one struct, following inherited ("$") base-class fields.

        Frostbite partitions only store the *own* fields of a type; the base
        class chain is expressed by a field named ``$`` with ``DataType.Void``
        whose ``type_index`` is the base type.  Gibbed flattens this away in
        ``PartitionFlattenedType``; we merge here so that e.g. a
        ``PlotLogicBooleanFlagRule`` exposes the ``Flag`` field it inherits
        from ``PlotLogicFlagRule``.
        """
        if depth > 12:
            return {"__error__": "nesting too deep"}
        seen = seen or frozenset()
        if type_index in seen:
            return {"__error__": "base class cycle"}
        seen = seen | {type_index}

        type_def = self.types[type_index]
        own: dict = {}
        base_type = None
        for field_index in range(type_def.field_start, type_def.field_start + type_def.field_count):
            f = self.fields[field_index]
            if f.data_type == DT_VOID and f.name == "$":
                base_type = f.type_index
                own["$"] = f"base:{self.types[base_type].label}"
                continue
            try:
                own[f.label] = self.read_value(base + f.data_offset, f.type_index,
                                               f.flags_raw, depth + 1)
            except PartitionError as exc:
                own[f.label] = f"<{exc}>"

        if base_type is not None and base_type != type_index:
            merged = self.struct(base_type, base, depth + 1, seen)
            merged.update(own)
            return merged
        return own

    def read_value(self, offset: int, type_index: int, flags_raw: int, depth: int = 0):
        e = self.endian
        data = self.data
        dt = (flags_raw >> 4) & 0x1F
        if dt == DT_VALUE:
            return self.struct(type_index, offset, depth)
        if dt == DT_CLASS:
            value = struct.unpack_from(e + "I", data, offset)[0]
            if value == 0:
                return None
            if value & 0x80000000:
                idx = value & 0x7FFFFFFF
                if idx < len(self.imports):
                    return {"__import__": self.imports[idx][1].text}
                return {"__import__": idx}
            idx = value - 1
            if 0 <= idx < len(self.instances):
                inst = self.instances[idx]
                return {"__instance__": inst.index, "__type__": self.types[inst.type_index].label}
            return {"__instance__": value - 1}
        if dt == DT_LIST:
            array_index = struct.unpack_from(e + "I", data, offset)[0]
            return self._read_array(array_index, depth)
        if dt == DT_STRING2:
            string_offset = struct.unpack_from(e + "I", data, offset)[0]
            if string_offset == 0xFFFFFFFF:
                return None
            end = data.find(b"\x00", string_offset)
            return data[string_offset:end if end >= 0 else len(data)].decode("utf-8", "replace")
        if dt == DT_ENUM:
            return struct.unpack_from(e + "I", data, offset)[0]
        if dt == DT_BOOLEAN:
            return data[offset] != 0
        if dt in _FIXED_SIZE:
            fmt = {
                DT_INT8: "b", DT_UINT8: "B", DT_INT16: "h", DT_UINT16: "H",
                DT_INT32: "i", DT_UINT32: "I", DT_INT64: "q", DT_UINT64: "Q",
                DT_FLOAT32: "f", DT_FLOAT64: "d",
            }.get(dt)
            if dt == DT_GUID:
                raw = data[offset:offset + 16]
                return (Guid.from_le_fields(raw) if e == "<" else Guid.from_be_fields(raw))
            if dt == DT_SHA1:
                return data[offset:offset + 20]
            if fmt:
                size = struct.calcsize(fmt)
                return struct.unpack_from(e + fmt, data, offset)[0]
        if dt == DT_VOID:
            return None
        raise PartitionError(f"unsupported DataType {_DT_NAMES.get(dt, dt)} at +{offset}")

    def _read_array(self, array_index: int, depth: int = 0):
        if array_index == 0xFFFFFFFF:
            return None
        if not (0 <= array_index < len(self.arrays)):
            return {"__array_error__": array_index}
        data_offset, item_count, type_index = self.arrays[array_index]
        type_def = self.types[type_index]
        if type_def.field_count != 1:
            return {"__array__": array_index, "items": item_count}
        member = self.fields[type_def.field_start]
        member_size = self._field_size(member)
        items = []
        base = self.string_table_size + self.array_offset + data_offset
        for i in range(min(item_count, 4096)):
            items.append(self.read_value(base + i * member_size, member.type_index,
                                         member.flags_raw, depth + 1))
        return items

    def _field_size(self, field: FieldDef) -> int:
        if field.data_type in _FIXED_SIZE:
            return _FIXED_SIZE[field.data_type]
        if field.data_type in (DT_VALUE, DT_ENUM):
            return self.types[field.type_index].data_size
        if field.data_type in (DT_CLASS, DT_LIST):
            return 4
        raise PartitionError(f"unsupported field size for {field.type_name}")

    # -- convenience --------------------------------------------------------
    def instance_objects(self):
        """Yield ``(instance, object_dict)`` for every instance."""
        for inst in self.instances:
            yield inst, self.struct(inst.type_index, inst.data_offset)

    def all_guids(self) -> list[tuple[str, Guid]]:
        """Every GUID-typed value in the partition, labelled by type/field path."""
        found: list[tuple[str, Guid]] = []
        for inst, obj in self.instance_objects():
            type_name = self.types[inst.type_index].label
            self._collect_guids(obj, type_name, found)
        return found

    def _collect_guids(self, value, path: str, out: list) -> None:
        if isinstance(value, Guid):
            out.append((path, value))
        elif isinstance(value, dict):
            for key, sub in value.items():
                self._collect_guids(sub, f"{path}.{key}", out)
        elif isinstance(value, list):
            for i, sub in enumerate(value):
                self._collect_guids(sub, f"{path}[{i}]", out)

    def find_raw(self, needle: bytes) -> list[int]:
        """Offsets inside the data blob where ``needle`` occurs verbatim."""
        hits = []
        start = 0
        while True:
            idx = self.data.find(needle, start)
            if idx < 0:
                return hits
            hits.append(idx)
            start = idx + 1

    def describe(self) -> list[str]:
        lines = [
            f"magic           0x{MAGIC:08X} ({self.buffer[:4].hex(' ')})",
            f"endian          {'little' if self.endian == '<' else 'big'}",
            f"partition GUID  {self.guid.text}",
            f"headerSize      {self.header_size}",
            f"dataSize        {self.data_size}",
            f"imports         {len(self.imports)}",
            f"instances       {len(self.instances)} ({self.named_instance_count} named, "
            f"{self.exported_instance_count} exported)",
            f"types           {len(self.types)}",
            f"fields          {len(self.fields)}",
            f"names           {len(self.names)}",
            f"arrays          {len(self.arrays)}",
            f"stringTableSize {self.string_table_size}",
            f"arrayOffset     {self.array_offset}",
        ]
        return lines
