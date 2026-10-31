"""Read, modify and re-emit a Frosty `.fbmod` (FBMODV2 / DbObject).

Round-trip is byte-identical for all 13 DbObject mods in the pack, so a modification is now just
"edit a value, re-encode". FROSTY v1 mods are not DbObjects and are rejected explicitly.

Usage:
  python fbmod_write.py <mod> <out> [--title NEW] [--author NEW] [--version NEW]
  python fbmod_write.py --selftest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "frostbite"))

from frostbite import dbwrite, dbobject  # noqa: E402

SCALARS = {"title", "author", "version", "category", "description", "gameProfile"}


class NotAFrostyMod(Exception):
    pass


def load(path: Path):
    data = path.read_bytes()
    reader = dbwrite.TypedReader(data, 0)
    root_tag = reader.u8()
    inner_tag, inner_value = reader.value(root_tag & 0x1F)
    if reader.pos != len(data):
        raise NotAFrostyMod(f"{len(data) - reader.pos} trailing byte(s): not a DbObject mod "
                            f"(FROSTY v1 mods are not supported)")
    return root_tag, inner_tag, inner_value


def save(root_tag: int, inner_tag: int, inner_value, path: Path) -> int:
    blob = bytes([root_tag]) + dbwrite.write_value(inner_tag, inner_value)
    path.write_bytes(blob)
    return len(blob)


def field(inner_value, name: str):
    for key, (tag, value) in inner_value:
        if key == name:
            return tag, value
    raise KeyError(name)


def set_field(inner_value, name: str, new_value) -> None:
    for index, (key, (tag, value)) in enumerate(inner_value):
        if key == name:
            inner_value[index] = (key, (tag, new_value))
            return
    raise KeyError(name)


def selftest() -> int:
    mods = sorted((Path(__file__).resolve().parent.parent / "Mass Effect Andromeda Mods").glob("*.fbmod"))
    identical = rejected = 0
    scratch = Path(__file__).resolve().parent / "scratch"
    for mod in mods:
        try:
            root_tag, inner_tag, inner_value = load(mod)
        except NotAFrostyMod:
            rejected += 1
            continue
        out = scratch / f"rt-{mod.name}"
        save(root_tag, inner_tag, inner_value, out)
        if out.read_bytes() == mod.read_bytes():
            identical += 1
        else:
            print(f"  DIFF {mod.name}")
    print(f"round-trip: {identical} identical, {rejected} not DbObject mods")

    # a real edit: change the title, re-emit, read it back with the original parser
    sample = next(m for m in mods if "Tempest Superstore Rank 01" in m.name)
    root_tag, inner_tag, inner_value = load(sample)
    _, old_title = field(inner_value, "title")
    set_field(inner_value, "title", old_title + " (AP)")
    out = scratch / "edited-title.fbmod"
    save(root_tag, inner_tag, inner_value, out)
    reread = dbobject.parse(out.read_bytes())
    assert reread["title"] == old_title + " (AP)", reread["title"]
    assert reread["resources"] == dbobject.parse(sample.read_bytes())["resources"], "resources changed!"
    print(f"edit: title {old_title!r} -> {reread['title']!r}, resources unchanged, "
          f"{out.stat().st_size} bytes")
    print("SELFTEST PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", nargs="?", type=Path)
    ap.add_argument("out", nargs="?", type=Path)
    ap.add_argument("--title"); ap.add_argument("--author"); ap.add_argument("--version")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not (args.mod and args.out):
        ap.error("mod and out are required unless --selftest")
    root_tag, inner_tag, inner_value = load(args.mod)
    for name in ("title", "author", "version"):
        new = getattr(args, name)
        if new is not None:
            set_field(inner_value, name, new)
    size = save(root_tag, inner_tag, inner_value, args.out)
    print(f"wrote {args.out} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
