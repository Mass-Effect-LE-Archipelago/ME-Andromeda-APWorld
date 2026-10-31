from pathlib import Path
p = Path("tools/frostbite/dbwrite.py")
s = p.read_text(encoding="utf-8")
# dispatch on the masked type but keep the raw tag byte (0x80 carries meaning)
s = s.replace('    def value(self, tag: int):\n        """Return (tag, value) with enough fidelity to re-encode."""\n',
              '    def value(self, tag: int):\n        """Return (raw tag, value): the raw byte keeps flags above 0x1F (e.g. 0x80)."""\n        t = tag & 0x1F\n')
for name in ("Bool", "String", "Int32", "Int64", "Float64", "Guid", "SHA1", "Bytes", "Array", "Object"):
    s = s.replace(f"if tag == ValueType.{name}:", f"if t == ValueType.{name}:")
    s = s.replace(f"if tag in (ValueType.{name},):", f"if t == ValueType.{name}:")
s = s.replace("out.append(self.value(tag & 0x1F))", "out.append(self.value(tag))")
s = s.replace("out.append((name, self.value(tag & 0x1F)))", "out.append((name, self.value(tag)))")
s = s.replace("def write_value(tag: int, value) -> bytes:\n", "def write_value(tag: int, value) -> bytes:\n    t = tag & 0x1F\n")
for name in ("Bool", "String", "Int32", "Int64", "Float64", "Guid", "SHA1", "Bytes", "Array", "Object"):
    s = s.replace(f"if tag == ValueType.{name}:", f"if t == ValueType.{name}:")
    s = s.replace(f"if tag in (ValueType.{name}, ValueType.SHA1, ValueType.Bytes):", f"if t in (ValueType.{name}, ValueType.SHA1, ValueType.Bytes):")
s = s.replace('if tag == ValueType.Guid, ValueType.SHA1, ValueType.Bytes:', 'if t in (ValueType.Guid, ValueType.SHA1, ValueType.Bytes):')
p.write_text(s, encoding="utf-8")
print("patched dbwrite.py")
