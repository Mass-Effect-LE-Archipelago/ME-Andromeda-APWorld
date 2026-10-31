from pathlib import Path
p = Path("tools/build_planet_mod.py")
s = p.read_text(encoding="utf-8")
s = s.replace("""    resources = get(inner, "resources")[1]
    resource = resources[0][1]  # (tag, object)
    obj = resource[1]""", """    resources = get(inner, "resources")[1]      # array value: [(elem_tag, object), ...]
    obj = resources[0][1]                       # the object as [(name, (tag, value)), ...]""")
s = s.replace("""    actions = get(inner, "actions")[1]
    action = actions[0][1][1]""", """    actions = get(inner, "actions")[1]
    action = actions[0][1]""")
p.write_text(s, encoding="utf-8")
print("patched builder")
