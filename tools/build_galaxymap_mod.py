"""Build the galaxy-map gate mod: open all 38 jumpable systems at once.

Every system's availability is the `AvailableFlag` on its `SystemData` row
(`game/space/systems/systemdata/systemdata_<system>`, 848-864 bytes).  This tool swaps that one
PlotFlagId for the engine's `alwaystrue` constant in all 38 rows and packages them as a single
`.fbmod` + `.archive`, following the same container recipe as `build_planet_mod.py`.

The multi-bundle rule is taken from a real Frosty mod (`betterDeconstruction.fbmod`: 920 resources,
2,146 actions): every asset is listed under several bundles and gets **one `modify` action per
listing bundle**.  Resource fields follow the same mod's measured semantics:

    sha1            sha1 of the NEW decompressed asset bytes
    originalSha1    the vanilla chunk sha1 from the superbundle (lets Frosty find the base chunk)
    originalSize    vanilla uncompressed size
    archiveOffset   the chunk's 8-byte header position in the archive
    compressedSize  8 + len(zstd frame)   (the whole slot, header included)
    uncompressedSize len(decompressed bytes)

Usage:
  python build_galaxymap_mod.py [--out DIR] [--title TEXT] [--dry-run]

Findings: docs/GALAXYMAP-GATE.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "frostbite"))

import fbmod  # noqa: E402
import fbmod_write  # noqa: E402
from frostbite import modarchive, vfs  # noqa: E402
from frostbite.partition import Partition  # noqa: E402

ALWAYSTRUE = uuid.UUID("bf899768-3614-11e5-aa63-b2e3b7222cc5")
PREFAB = "game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap"
SYSTEMDATA = "game/space/systems/systemdata/systemdata_"
TEMPLATE_MOD = ROOT / "Mass Effect Andromeda Mods" / "betterDeconstruction.fbmod"
TEMPLATE_ARCHIVE = ROOT / "Mass Effect Andromeda Mods" / "betterDeconstruction_01.archive"


def guid_orders(g: uuid.UUID) -> dict[str, bytes]:
    raw = g.bytes
    return {"be": raw, "le": raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:],
            "rev": raw[::-1]}


def availability_guid(part: Partition) -> str:
    for _inst, obj in part.instance_objects():
        if not isinstance(obj, dict):
            continue
        ref = ((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid")
        if ref is not None:
            return str(ref).lower()
    raise KeyError("no AvailableFlag in partition")


def open_availability(partition: bytes) -> tuple[bytes, str, int]:
    """Swap the partition's AvailableFlag for alwaystrue. Returns (patched, old guid, swaps)."""
    part = Partition(partition)
    old = availability_guid(part)
    patched, swaps = partition, 0
    for label, pattern in guid_orders(uuid.UUID(old)).items():
        count = patched.count(pattern)
        if count:
            patched = patched.replace(pattern, guid_orders(ALWAYSTRUE)[label])
            swaps += count
    return patched, old, swaps


def conditions(part: Partition):
    """Yield (instance, base-type-index) for every PlotConditionNotificationEntityData."""
    for inst in part.instances:
        td = part.types[inst.type_index]
        base = None
        for i in range(td.field_start, td.field_start + td.field_count):
            f = part.fields[i]
            if f.label == "$":
                base = f.type_index
        if base is not None and part.types[base].label == "PlotConditionNotificationEntityData":
            yield inst, base


def patch_prefab(data: bytes, flags: list[str]) -> tuple[bytes, int, int]:
    """Make every condition fire at prefab start, and force its flag true.

    The conditions are edge-triggered (`TriggerOnValueChange: true`, `CheckOnStart: false`) and
    send OnTrue -> Enable / OnFalse -> Disable to their spawned map objects.  A flag that is
    already true at load never changes, so nothing is ever enabled.  Setting CheckOnStart makes
    the condition evaluate at spawn, and alwaystrue makes that evaluation true.
    """
    part = Partition(data)
    patched = bytearray(data)
    toggled = 0
    for inst, base in conditions(part):
        td = part.types[base]
        for i in range(td.field_start, td.field_start + td.field_count):
            f = part.fields[i]
            if f.label == "CheckOnStart":
                # inst.data_offset is relative to the data blob, not to the file
                patched[part.header_size + inst.data_offset + f.data_offset] = 1
                toggled += 1
    out = bytes(patched)
    swaps = 0
    for flag in dict.fromkeys(flags):
        for label, pattern in guid_orders(uuid.UUID(flag)).items():
            count = out.count(pattern)
            if count:
                out = out.replace(pattern, guid_orders(ALWAYSTRUE)[label])
                swaps += count
    return out, toggled, swaps


def prefab_ok(data: bytes, expect_true_flags: bool = True) -> bool:
    part = Partition(data)
    count = 0
    for inst, base in conditions(part):
        td = part.types[base]
        off = next(inst.data_offset + part.fields[i].data_offset
                   for i in range(td.field_start, td.field_start + td.field_count)
                   if part.fields[i].label == "CheckOnStart")
        if part.data[off] != 1:
            return False
        count += 1
    if not expect_true_flags:
        return count == 38
    flags = {str(g).lower() for path, g in part.all_guids() if "PlotFlagId" in path}
    return count == 38 and flags == {str(ALWAYSTRUE)}


def get(entry_list, name):
    for key, pair in entry_list:
        if key == name:
            return pair
    raise KeyError(name)


def put(entry_list, name, value) -> None:
    for index, (key, (_tag, _old)) in enumerate(entry_list):
        if key == name:
            entry_list[index] = (key, (_tag, value))
            return
    raise KeyError(name)


def check_offset_convention(template_archive: Path, parsed_template: dict) -> None:
    """Prove the archiveOffset convention before copying it.

    Measured on `betterDeconstruction` (920 resources / 920 chunks):
      * resource.archiveOffset == the chunk's 8-byte header position in the archive;
      * resource.compressedSize == 8 + len(zstd frame)  (the whole slot, header included);
      * resource.uncompressedSize == len(decompressed bytes).
    """
    chunks = modarchive.parse(template_archive.read_bytes())
    res = parsed_template["resources"]
    consecutive = all(
        res[i]["offset"] + res[i]["compressed_size"] == res[i + 1]["offset"]
        for i in range(len(res) - 1)
    )
    sizes_ok = all(
        r["compressed_size"] == len(c.compressed) + 8 and r["uncompressed_size"] == len(c.data)
        for r, c in zip(res, chunks)
    )
    print(f"template offset convention: archiveOffset = chunk header offset, "
          f"compressedSize = 8 + frame; {len(chunks)} chunks, consecutive={consecutive}, "
          f"sizes match={sizes_ok}")
    if not (consecutive and sizes_ok):
        raise SystemExit("template archiveOffset convention is not what this tool assumes")


def system_assets(game) -> list[str]:
    return sorted(n for n in game.iter_names(SYSTEMDATA)
                  if n.startswith(SYSTEMDATA) and "/" not in n[len(SYSTEMDATA):])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "galaxy-mods")
    ap.add_argument("--title", default="AP Galaxy Map Unlock (all 38 systems)")
    ap.add_argument("--name", default="AP_GalaxyMap_AllSystems",
                    help="output file stem; change it if Frosty caches the old mod")
    ap.add_argument("--version", default="1.01")
    ap.add_argument("--prefab-only", action="store_true",
                    help="patch only spawnedgalaxymap (CheckOnStart on the 38 conditions, real "
                         "flags kept); this is the H1 experiment from HANDOFF-GALAXYMAP.md")
    ap.add_argument("--rows-only", action="store_true",
                    help="patch only the 38 SystemData rows (the v1 experiment)")
    ap.add_argument("--dry-run", action="store_true", help="verify the patches, write nothing")
    args = ap.parse_args()

    game = vfs.Game()
    names = system_assets(game)
    print(f"systems: {len(names)}")

    root_tag, inner_tag, inner = fbmod_write.load(TEMPLATE_MOD)
    template_chunks = modarchive.parse(TEMPLATE_ARCHIVE.read_bytes())
    check_offset_convention(TEMPLATE_ARCHIVE, fbmod.parse(TEMPLATE_MOD))
    resource_array = get(inner, "resources")[1]
    action_array = get(inner, "actions")[1]
    resource_elem_tag = resource_array[0][0]
    action_elem_tag = action_array[0][0]
    template_resource = copy.deepcopy(resource_array[0][1])
    template_action = copy.deepcopy(action_array[0][1])
    print(f"template: {len(template_chunks)} chunks, resource fields "
          f"{[k for k, _v in template_resource]}")

    chunks: list = []
    resources: list = []
    actions: list = []
    offset = 0
    problems = 0

    # every asset the mod overrides, in the order it goes into the archive
    work: list[tuple[str, bytes]] = []
    flags_seen: list[str] = []
    if not args.prefab_only:
        for name in names:
            raw, _location = game.chunk_data(game.resolve(name))
            patched, old_flag, swaps = open_availability(raw)
            after = Partition(patched)                 # reparse: header invariants must hold
            if availability_guid(after) != str(ALWAYSTRUE):
                print(f"  FAIL {name}: AvailableFlag did not change")
                problems += 1
                continue
            if len(patched) != len(raw) or len(after.instances) != len(Partition(raw).instances):
                print(f"  FAIL {name}: size/instance count changed")
                problems += 1
                continue
            if swaps != 1:
                print(f"  WARN {name}: {swaps} byte swap(s), expected 1")
            flags_seen.append(old_flag)
            work.append((name, patched))
    else:
        # keep the real flags: only CheckOnStart changes, so the conditions re-evaluate at spawn
        for name in names:
            raw, _location = game.chunk_data(game.resolve(name))
            flags_seen.append(availability_guid(Partition(raw)))

    prefab_raw, _location = game.chunk_data(game.resolve(PREFAB))
    if args.rows_only:
        print("rows-only mode: prefab left vanilla")
    else:
        swap_flags = [] if args.prefab_only else flags_seen
        prefab_patched, toggled, pf_swaps = patch_prefab(prefab_raw, swap_flags)
        print(f"prefab: {len(prefab_raw)} B, CheckOnStart set on {toggled} condition(s), "
              f"{pf_swaps} flag GUID(s) -> alwaystrue, "
              f"reparse ok={prefab_ok(prefab_patched, expect_true_flags=bool(swap_flags))}")
        if toggled != 38 or not prefab_ok(prefab_patched, expect_true_flags=bool(swap_flags)):
            print("  FAIL: prefab patch did not verify")
            problems += 1
        work.append((PREFAB, prefab_patched))

    for index, (name, patched) in enumerate(work):
        record = game.resolve(name)
        raw = None
        if name == PREFAB:
            raw = prefab_raw

        chunk = modarchive.Chunk(offset=0, size=len(patched), marker=modarchive.MARKER,
                                 compressed=b"")
        modarchive.replace(chunk, patched)
        chunks.append(chunk)

        res = copy.deepcopy(template_resource)
        put(res, "name", name)
        put(res, "type", "ebx")
        put(res, "sha1", hashlib.sha1(patched).digest())        # sha1 of the new asset bytes
        put(res, "originalSha1", record.sha1)                   # vanilla chunk sha1 from the .sb
        put(res, "originalSize", record.original_size)
        put(res, "archiveOffset", offset)
        put(res, "compressedSize", len(chunk.compressed) + 8)
        put(res, "uncompressedSize", len(patched))
        resources.append((resource_elem_tag, res))
        offset += len(chunk.compressed) + 8

        bundles = list(dict.fromkeys(r.bundle for r in game.find(name)))
        for bundle in bundles:
            act = copy.deepcopy(template_action)
            put(act, "resourceId", index)
            put(act, "type", "modify")
            put(act, "bundle", bundle)
            actions.append((action_elem_tag, act))
        if index % 10 == 0 or name == PREFAB:
            print(f"  [{index:2d}] {name.rsplit('/', 1)[-1]:22s} {len(patched):5d} B  "
                  f"{len(bundles)} bundle action(s)")

    print(f"\npatched {len(chunks)} asset(s), {len(actions)} action(s), "
          f"{offset:,} compressed byte(s); problems: {problems}")
    if problems or len(chunks) != len(work):
        print("refusing to package an incomplete mod")
        return 1
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    put(inner, "resources", resources)
    put(inner, "actions", actions)
    put(inner, "title", args.title)
    put(inner, "author", "Mass Effect Andromeda AP")
    put(inner, "version", args.version)
    put(inner, "description",
        "Sets AvailableFlag to alwaystrue on all 38 SystemData rows AND makes the galaxy-map "
        "prefab's 38 plot conditions check on start, so every system is revealed when the map "
        "opens regardless of story progress.")
    archive_bytes = modarchive.rebuild(chunks)

    args.out.mkdir(parents=True, exist_ok=True)
    mod_path = args.out / f"{args.name}.fbmod"
    archive_path = args.out / f"{args.name}_01.archive"
    size = fbmod_write.save(root_tag, inner_tag, inner, mod_path)
    archive_path.write_bytes(archive_bytes)
    print(f"wrote {mod_path.name} ({size:,} bytes) and {archive_path.name} "
          f"({len(archive_bytes):,} bytes)")

    # -- verify what landed on disk, from the files, not from memory ----------------------
    parsed = fbmod.parse(mod_path)
    _rt, _it, reread = fbmod_write.load(mod_path)
    stored = [dict((k, v) for k, (_t, v) in obj) for _tag, obj in get(reread, "resources")[1]]
    rebuilt = modarchive.parse(archive_path.read_bytes())
    ok = True
    ok &= parsed["format"] == "FBMODV2" and len(parsed["assets"]) == len(work)
    ok &= len(parsed["resources"]) == len(work) and len(parsed["actions"]) == len(actions)
    for res, chunk, (name, _patched) in zip(stored, rebuilt, work):
        rec = game.resolve(name)
        ok &= res["name"] == name and res["type"] == "ebx"
        ok &= res["sha1"] == hashlib.sha1(chunk.data).digest()
        ok &= res["originalSha1"] == rec.sha1
        ok &= res["originalSize"] == rec.original_size
        ok &= res["archiveOffset"] == chunk.offset
        ok &= res["compressedSize"] == len(chunk.compressed) + 8
        ok &= res["uncompressedSize"] == len(chunk.data)
        ok &= (prefab_ok(chunk.data, expect_true_flags=not args.prefab_only)
               if name == PREFAB
               else availability_guid(Partition(chunk.data)) == str(ALWAYSTRUE))
    covered = {a["bundle"] for a in parsed["actions"]}
    expected = {b for n, _p in work for b in (r.bundle for r in game.find(n))}
    print(f"verify: format={parsed['format']} assets={len(parsed['assets'])} "
          f"resources={len(parsed['resources'])} actions={len(parsed['actions'])}")
    print(f"verify: names/sha1/originalSha1/originalSize/offsets/sizes + "
          f"flags/CheckOnStart in every chunk: {bool(ok)}")
    print(f"verify: bundle coverage {len(covered)}/{len(expected)} "
          f"{'complete' if covered == expected else 'MISSING ' + str(sorted(expected - covered))}")
    print(f"verify: all resource names/sizes match: {ok}")
    return 0 if ok and covered == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
