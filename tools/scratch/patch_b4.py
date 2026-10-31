from pathlib import Path
p = Path("tools/build_planet_mod.py")
s = p.read_text(encoding="utf-8")
s = s.replace("""    modarchive.replace(chunks[0], patched)
    archive_bytes = modarchive.rebuild(chunks)""",
"""    modarchive.replace(chunks[0], patched)
    # keep ONLY the chunk we are overriding: the template's other 919 assets must not ship
    chunks = chunks[:1]
    archive_bytes = modarchive.rebuild(chunks)""")
s = s.replace("""    put(obj, "uncompressedSize", len(patched))""",
"""    put(obj, "uncompressedSize", len(patched))
    put(inner, "resources", resources[:1])   # exactly one overridden asset""")
s = s.replace("""    put(action, "bundle", record.bundle)""",
"""    put(action, "bundle", record.bundle)
    put(inner, "actions", actions[:1])""")
p.write_text(s, encoding="utf-8")
print("builder now emits a single-asset mod")
