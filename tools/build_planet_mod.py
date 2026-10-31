"""Build a gameplay mod: override one galaxy-map destination with its gate opened.

Takes the destination's EBX partition from the game, swaps the `alwaysfalse` condition import for
`alwaystrue`, then rebuilds a real `.fbmod` + `.archive` pair around it using an existing mod as
the container template.

Usage: python build_planet_mod.py <destination-name> [--out DIR]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))

import fbmod  # noqa: E402
import fbmod_write  # noqa: E402
from frostbite import modarchive, vfs  # noqa: E402

FALSE = uuid.UUID("c6660dbe-3614-11e5-aa63-b2e3b7222cc5")
TRUE = uuid.UUID("bf899768-3614-11e5-aa63-b2e3b7222cc5")
TEMPLATE_MOD = ROOT / "Mass Effect Andromeda Mods" / "betterDeconstruction.fbmod"
TEMPLATE_ARCHIVE = ROOT / "Mass Effect Andromeda Mods" / "betterDeconstruction_01.archive"


def guid_orders(g: uuid.UUID) -> dict[str, bytes]:
    raw = g.bytes
    little = raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:]
    return {"be": raw, "le": little, "rev": raw[::-1]}


def open_gate(partition: bytes) -> tuple[bytes, int]:
    patched, swaps = partition, 0
    for label, pattern in guid_orders(FALSE).items():
        count = patched.count(pattern)
        if count:
            patched = patched.replace(pattern, guid_orders(TRUE)[label])
            swaps += count
    return patched, swaps


def get(entry_list, name):
    for key, pair in entry_list:
        if key == name:
            return pair
    raise KeyError(name)


def put(entry_list, name, value) -> None:
    for index, (key, (tag, _old)) in enumerate(entry_list):
        if key == name:
            entry_list[index] = (key, (tag, value))
            return
    raise KeyError(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("destination")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "planet-mods")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    destination = args.destination
    game = vfs.Game()
    record = game.resolve(destination)
    raw_partition, _ = game.chunk_data(record)
    patched, swaps = open_gate(raw_partition)
    print(f"{destination}: partition {len(raw_partition)} bytes, {swaps} alwaysfalse reference(s) -> alwaystrue")
    if swaps == 0:
        print("  nothing to swap: this destination carries no alwaysfalse gate")
        return 1

    root_tag, inner_tag, inner = fbmod_write.load(TEMPLATE_MOD)
    chunks = modarchive.parse(TEMPLATE_ARCHIVE.read_bytes())
    print(f"  template: {len(chunks)} chunks; replacing chunk 0 "
          f"({len(chunks[0].data)} bytes) with the destination partition")
    modarchive.replace(chunks[0], patched)
    # keep ONLY the chunk we are overriding: the template's other 919 assets must not ship
    chunks = chunks[:1]
    archive_bytes = modarchive.rebuild(chunks)

    resources = get(inner, "resources")[1]      # array value: [(elem_tag, object), ...]
    obj = resources[0][1]                       # the object as [(name, (tag, value)), ...]
    put(obj, "name", destination)
    put(obj, "type", "ebx")
    put(obj, "archiveOffset", 0)
    put(obj, "compressedSize", len(chunks[0].compressed))
    put(obj, "uncompressedSize", len(patched))
    put(inner, "resources", resources[:1])   # exactly one overridden asset

    actions = get(inner, "actions")[1]
    action = actions[0][1]
    put(action, "resourceId", 0)
    put(action, "type", "modify")
    put(action, "bundle", record.bundle)
    put(inner, "actions", actions[:1])

    title = args.title or f"AP Planet Unlock: {destination.rsplit('/', 1)[-1]}"
    put(inner, "title", title)
    put(inner, "author", "Mass Effect Andromeda AP")
    put(inner, "description", f"Overrides {destination} with its alwaysfalse gate swapped to alwaystrue.")

    args.out.mkdir(parents=True, exist_ok=True)
    stem = "AP_" + destination.rsplit("/", 1)[-1]
    mod_path = args.out / f"{stem}.fbmod"
    archive_path = args.out / f"{stem}_01.archive"
    size = fbmod_write.save(root_tag, inner_tag, inner, mod_path)
    archive_path.write_bytes(archive_bytes)
    print(f"  wrote {mod_path.name} ({size} bytes) and {archive_path.name} ({len(archive_bytes)} bytes)")

    reparsed = fbmod.parse(mod_path) if hasattr(fbmod, "parse") else None
    if reparsed:
        print(f"  inventory reads it back: {reparsed['title']} | assets {len(reparsed['assets'])}")
    rebuilt = modarchive.parse(archive_path.read_bytes())
    print(f"  archive re-parses: {len(rebuilt)} chunks, chunk0 {len(rebuilt[0].data)} bytes, "
          f"consistent {all(len(c.data) == c.size for c in rebuilt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
