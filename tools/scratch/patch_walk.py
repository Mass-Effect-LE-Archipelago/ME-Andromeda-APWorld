from pathlib import Path
p = Path("tools/probe_gate_fields.py")
s = p.read_text(encoding="utf-8")
s = s.replace("""    if isinstance(value, dict):""", """    if isinstance(value, str):
        low = value.lower()
        if FALSE_GUID in low or TRUE_GUID in low:
            hits.append((path, "false" if FALSE_GUID in low else "true"))
        return
    if isinstance(value, dict):""")
p.write_text(s, encoding="utf-8")
print("patched walker")
