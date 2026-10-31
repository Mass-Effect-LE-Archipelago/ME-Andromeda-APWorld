from pathlib import Path
p = Path("tools/build_planet_mod.py")
s = p.read_text(encoding="utf-8").replace("import fbmod_write  # noqa: E402", "import fbmod  # noqa: E402\nimport fbmod_write  # noqa: E402")
p.write_text(s, encoding="utf-8")
print("import added")
