"""The galaxy-map gate: name the prefab, decode the system rows, prove the flag chain.

    python tools\\probe_galaxymap_prefab.py who        # which asset is tools/scratch/galaxymap.bin?
    python tools\\probe_galaxymap_prefab.py rows       # every *_galaxydataasset_autobundle
    python tools\\probe_galaxymap_prefab.py row aya_01 kadara_01    # full dump of two galaxy-data rows
    python tools\\probe_galaxymap_prefab.py part <asset> ...       # types, imports, connections
    python tools\\probe_galaxymap_prefab.py full <asset> ...       # every instance and field
    python tools\\probe_galaxymap_prefab.py map        # resolve spawnedgalaxymap's 46 imports
    python tools\\probe_galaxymap_prefab.py avail      # SystemData AvailableFlag per system
    python tools\\probe_galaxymap_prefab.py matrix     # flags true per save (all zero)
    python tools\\probe_galaxymap_prefab.py unlock     # galaxymap_unlock_* -> systems
    python tools\\probe_galaxymap_prefab.py verify     # the three flag sets agree
    python tools\\probe_galaxymap_prefab.py locators [system ...]
    python tools\\probe_galaxymap_prefab.py jumpgraph  # JumpToSystem edges, connectivity
    python tools\\probe_galaxymap_prefab.py gate       # pre-flight AvailableFlag -> alwaystrue
    python tools\\probe_galaxymap_prefab.py writers <flag-guid> ...  # who references a flag

Findings: docs/GALAXYMAP-GATE.md.  All output goes to stdout; nothing is written.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite import vfs  # noqa: E402
from frostbite.partition import Partition, PartitionError  # noqa: E402

GALAXYMAP_BIN = ROOT / "tools" / "scratch" / "galaxymap.bin"
GALAXYMAP_GUID = "e9d830c0-8980-11e5-b9be-d95347869af1"
PREFIX = "game/space/systems/"
SUFFIX = "_galaxydataasset_autobundle"


def partition_or_none(game, name):
    try:
        data, _ = game.chunk_data(game.resolve(name))
        return data, Partition(data)
    except (vfs.AssetError, PartitionError) as exc:
        return None, exc


def cmd_who(game) -> int:
    want = Partition(GALAXYMAP_BIN.read_bytes()).guid.text
    size = GALAXYMAP_BIN.stat().st_size
    print(f"galaxymap.bin  {size} bytes  partition-guid {want}")
    index = game.index()
    candidates = [
        name for name, rows in index.items()
        if rows[0].kind == "ebx" and rows[0].original_size == size
    ]
    print(f"ebx assets with originalSize == {size}: {len(candidates)}")
    for name in sorted(candidates):
        data, part = partition_or_none(game, name)
        if part is None:
            print(f"  {name}  <unreadable: {part}>")
            continue
        mark = "<= MATCH" if part.guid.text == want else ""
        print(f"  {name}  guid={part.guid.text} {mark}")
    return 0


def rows(game) -> list[str]:
    names = [n for n in game.iter_names(PREFIX) if n.startswith(PREFIX) and n.endswith(SUFFIX)]
    return sorted(names)


def cmd_rows(game) -> int:
    names = rows(game)
    print(f"galaxy data rows: {len(names)}")
    tables: list[tuple[str, dict]] = []
    for name in names:
        data, part = partition_or_none(game, name)
        if part is None:
            print(f"  {name}  <unreadable: {part}>")
            continue
        objs = [o for _i, o in part.instance_objects() if isinstance(o, dict)]
        merged: dict = {}
        for o in objs:
            merged.update(o)
        merged["__types__"] = sorted({str(o.get("$", "?")) for o in objs})
        merged["__instances__"] = len(objs)
        merged["__imports__"] = len(part.imports)
        tables.append((name[len(PREFIX):-len(SUFFIX)], merged))

    keys: list[str] = []
    for _label, m in tables:
        for k in m:
            if k not in keys:
                keys.append(k)
    print(f"{'system':14s} " + " ".join(f"{k[:22]:22s}" for k in keys))
    for label, m in tables:
        cells = []
        for k in keys:
            v = m.get(k, "-")
            cells.append(f"{str(v)[:22]:22s}")
        print(f"{label:14s} " + " ".join(cells))
    return 0


def cmd_row(game, labels: list[str]) -> int:
    for label in labels:
        name = f"{PREFIX}{label}{SUFFIX}"
        data, part = partition_or_none(game, name)
        print(f"=== {name}  ({len(data) if data else 0} bytes)")
        if part is None:
            print(f"  <unreadable: {part}>")
            continue
        print(f"  guid={part.guid.text} instances={len(part.instances)} "
              f"types={len(part.types)} imports={len(part.imports)}")
        for i, p in enumerate(part.imports):
            print(f"  import[{i}] partition={p[0].text} instance={p[1].text}")
        for inst, obj in part.instance_objects():
            print(f"  -- instance {inst.index} type={part.types[inst.type_index].label}")
            for k, v in obj.items():
                print(f"     {k:28s} {str(v)[:110]}")
    return 0


def cmd_part(game, names: list[str]) -> int:
    import collections

    for name in names:
        data, part = partition_or_none(game, name)
        print(f"=== {name}  ({len(data) if data else 0} bytes)")
        if part is None:
            print(f"  <unreadable: {part}>")
            continue
        print(f"  guid={part.guid.text} instances={len(part.instances)} "
              f"types={len(part.types)} imports={len(part.imports)} arrays={len(part.arrays)}")
        objs = [o for _i, o in part.instance_objects() if isinstance(o, dict)]
        for kind, n in collections.Counter(str(o.get("$", "?")).replace("base:", "")
                                           for o in objs).most_common():
            print(f"  {n:4d}  {kind}")
        print(f"  imports: {len(part.imports)}")
        for i, (pg, ig) in enumerate(part.imports[:40]):
            print(f"    import[{i}] partition={pg.text} instance={ig.text}")
        for bp in (o for o in objs if "PrefabBlueprint" in str(o.get("$", ""))):
            for key in ("PropertyConnections", "LinkConnections", "EventConnections",
                        "Objects", "Interface", "DynamicDataContainers"):
                val = bp.get(key)
                if isinstance(val, list):
                    print(f"    {key}: {len(val)} entries")
                elif val is not None:
                    print(f"    {key}: {str(val)[:80]}")
    return 0


def cmd_map(game, prefixes: list[str]) -> int:
    """Index partition GUID -> asset name for the given subtrees, then resolve imports."""
    import collections

    seen: dict[str, str] = {}
    scanned = 0
    for prefix in prefixes:
        for name in game.iter_names(prefix):
            if not name.startswith(prefix):
                continue
            data, part = partition_or_none(game, name)
            scanned += 1
            if part is None:
                continue
            seen[part.guid.text] = name
    print(f"indexed {len(seen)} partitions from {scanned} asset(s)")

    for name in ("game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap",):
        data, part = partition_or_none(game, name)
        print(f"\n{name}: {len(part.imports)} import(s)")
        hits = collections.Counter()
        for i, (pg, ig) in enumerate(part.imports):
            target = seen.get(pg.text, "?")
            hits[target] += 1
            print(f"  [{i:2d}] partition={pg.text} instance={ig.text}  -> {target}")
        print("\nresolved targets by asset:")
        for target, n in hits.most_common():
            print(f"  {n:3d}  {target}")
    return 0


def cmd_full(game, names: list[str]) -> int:
    for name in names:
        data, part = partition_or_none(game, name)
        print(f"=== {name}  ({len(data) if data else 0} bytes)")
        if part is None:
            print(f"  <unreadable: {part}>")
            continue
        print(f"  guid={part.guid.text} instances={len(part.instances)} "
              f"types={len(part.types)} imports={len(part.imports)}")
        for i, (pg, ig) in enumerate(part.imports):
            print(f"  import[{i}] partition={pg.text} instance={ig.text}")
        for inst, obj in part.instance_objects():
            g = inst.guid.hex() if inst.guid else "-"
            print(f"  -- instance {inst.index} type={part.types[inst.type_index].label} guid={g}")
            for k, v in obj.items():
                print(f"     {k:32s} {str(v)[:120]}")
    return 0


LADDER = [
    "Careerb191e387-Chapter0", "Careerb191e387-Chapter1", "Careerb191e387-Chapter51",
    "Careerb191e387-Chapter30", "Careerb191e387-Chapter4", "Careerb191e387-Chapter31",
    "Careerb191e387-Chapter6", "Careerb191e387-Chapter53", "Careerb191e387-Chapter33",
    "Careerb191e387-0ManualSave", "Careerb191e387-Chapter34", "Careerb191e387-Chapter10",
    "Careerb191e387-Mission",
]
SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"


def cmd_avail(game) -> int:
    import profsave3 as p  # noqa: E402

    systems = []
    prefix = "game/space/systems/systemdata/systemdata_"
    for name in game.iter_names(prefix):
        if not name.startswith(prefix) or "/" in name[len(prefix):]:
            continue
        _data, part = partition_or_none(game, name)
        if part is None:
            continue
        obj = next((o for _i, o in part.instance_objects() if isinstance(o, dict)), {})
        avail = (((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        visited = (((obj.get("VisitedFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        systems.append((name[len(prefix):], str(avail), str(visited)))

    saves = []
    for label in LADDER:
        path = SAVE_DIR / label
        if not path.is_file():
            continue
        save = p.load(path)
        flags = {}
        for kind in ("bools", "ints", "floats"):
            flags.update(save.plot.get(kind, {}))
        saves.append((label, flags))

    def first_true(flags_by_save, guid):
        for i, (label, flags) in enumerate(flags_by_save):
            if flags.get(guid) is True:
                return f"{i}:{label.split('-', 1)[1]}"
        return "-"

    print(f"{'system':14s} {'available flag':38s} {'first true':22s} {'visited flag':38s} "
          f"{'first visited':16s}")
    for label, avail, visited in systems:
        print(f"{label:14s} {avail:38s} {first_true(saves, avail):22s} "
              f"{visited:38s} {first_true(saves, visited):16s}")
    print(f"\nladder saves loaded: {len(saves)}/{len(LADDER)}")
    return 0


def cmd_matrix(game) -> int:
    """Per save, how many SystemData AvailableFlags / VisitedFlags are true."""
    import profsave3 as p  # noqa: E402

    prefix = "game/space/systems/systemdata/systemdata_"
    table = []
    for name in game.iter_names(prefix):
        if not name.startswith(prefix) or "/" in name[len(prefix):]:
            continue
        _data, part = partition_or_none(game, name)
        if part is None:
            continue
        obj = next((o for _i, o in part.instance_objects() if isinstance(o, dict)), {})
        avail = (((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        visited = (((obj.get("VisitedFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        table.append((name[len(prefix):], str(avail), str(visited)))

    print(f"systems: {len(table)}")
    for path in sorted(SAVE_DIR.iterdir(), key=lambda q: q.name):
        if not path.is_file() or not path.name.startswith("Career"):
            continue
        try:
            save = p.load(path)
        except Exception as exc:  # noqa: BLE001
            print(f"  {path.name:34s} <unreadable: {exc}>")
            continue
        bools = save.plot.get("bools", {})
        ints = save.plot.get("ints", {})
        true_avail = [s for s, g, _v in table if bools.get(g) is True or ints.get(g) == 1]
        true_visited = [s for s, _g, v in table if bools.get(v) is True or ints.get(v) == 1]
        print(f"  {path.name:34s} bools={len(bools):6d} avail_true={len(true_avail):2d} "
              f"visited_true={len(true_visited):2d}  {','.join(true_avail[:12])}")
    return 0


def cmd_unlock(game) -> int:
    """Map each galaxymap_unlock_* plot asset to the systems whose AvailableFlag it sets."""
    prefix = "game/space/systems/systemdata/systemdata_"
    by_flag: dict[str, str] = {}
    for name in game.iter_names(prefix):
        if not name.startswith(prefix) or "/" in name[len(prefix):]:
            continue
        _data, part = partition_or_none(game, name)
        if part is None:
            continue
        obj = next((o for _i, o in part.instance_objects() if isinstance(o, dict)), {})
        avail = (((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        if avail is not None:
            by_flag[str(avail).lower()] = name[len(prefix):]

    unlock = "game/plots/systems/space/galaxymap_unlock_"
    total: set[str] = set()
    for name in sorted(game.iter_names(unlock)):
        if not name.startswith(unlock):
            continue
        _data, part = partition_or_none(game, name)
        if part is None:
            print(f"{name}: <unreadable>")
            continue
        flags = []
        for path, guid in part.all_guids():
            if "PlotFlagId" in path:
                flags.append((str(guid).lower(), path))
        unique = dict.fromkeys(g for g, _p in flags)
        systems = [by_flag.get(g, f"?{g}") for g in unique]
        total.update(unique)
        print(f"{name[len(unlock):]:20s} {len(unique):2d} flag(s) -> "
              f"{', '.join(systems)}")
    print(f"\ndistinct flags written by unlock assets: {len(total)}")
    print(f"systems with an AvailableFlag: {len(by_flag)}")
    missing = [s for g, s in by_flag.items() if g not in total]
    print(f"systems not written by any unlock asset: {len(missing)}: {', '.join(sorted(missing))}")
    return 0


def cmd_writers(game, guids: list[str], prefixes: list[str]) -> int:
    """Find every asset that contains one of the given flag GUIDs as literal bytes."""
    import uuid

    def patterns(text: str) -> list[bytes]:
        raw = uuid.UUID(text).bytes
        little = raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:]
        return [raw, little, raw[::-1]]

    wanted = {g.lower(): patterns(g) for g in guids}
    found: dict[str, list[str]] = {}
    scanned = 0
    for prefix in prefixes:
        for name in game.iter_names(prefix):
            if not name.startswith(prefix):
                continue
            try:
                data, _ = game.chunk_data(game.resolve(name))
            except Exception:  # noqa: BLE001
                continue
            scanned += 1
            for g, pats in wanted.items():
                if any(p in data for p in pats):
                    found.setdefault(g, []).append(name)
            if scanned % 500 == 0:
                print(f"  ... {scanned} scanned, "
                      f"{sum(len(v) for v in found.values())} hit(s)", flush=True)
    print(f"scanned {scanned} asset(s) under {', '.join(prefixes)}")
    for g in guids:
        hits = found.get(g.lower(), [])
        print(f"{g}: {len(hits)} writer(s)")
        for name in hits:
            print(f"   {name}")
    return 0


ALWAYSTRUE = "bf899768-3614-11e5-aa63-b2e3b7222cc5"


def cmd_gate(game) -> int:
    """Pre-flight the mod recipe: swap each AvailableFlag for alwaystrue and reparse."""
    import uuid

    def orders(text: str) -> dict[str, bytes]:
        raw = uuid.UUID(text).bytes
        return {
            "be": raw,
            "le": raw[:4][::-1] + raw[4:6][::-1] + raw[6:8][::-1] + raw[8:],
            "rev": raw[::-1],
        }

    true_orders = orders(ALWAYSTRUE)
    prefix = "game/space/systems/systemdata/systemdata_"
    names = sorted(n for n in game.iter_names(prefix)
                   if n.startswith(prefix) and "/" not in n[len(prefix):])
    print(f"{'system':14s} {'available flag':38s} {'hits(be/le/rev)':16s} {'bytes':6s} reparse")
    bad = 0
    for name in names:
        data, part = partition_or_none(game, name)
        if part is None:
            print(f"{name}: unreadable")
            bad += 1
            continue
        obj = next((o for _i, o in part.instance_objects() if isinstance(o, dict)), {})
        avail = str((((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid")))
        pats = orders(avail)
        hits = [data.count(p) for p in pats.values()]
        patched = data
        for label, pat in pats.items():
            patched = patched.replace(pat, true_orders[label])
        try:
            after = Partition(patched)
            ok = (len(after.instances) == len(part.instances)
                  and len(after.imports) == len(part.imports)
                  and len(patched) == len(data))
        except PartitionError as exc:
            ok = f"PARSE FAILED: {exc}"
        if not ok:
            bad += 1
        print(f"{name[len(prefix):]:14s} {avail:38s} {str(hits):16s} {len(data):6d} {ok}")
    print(f"\n{len(names)} system(s); problems: {bad}")
    return 0


def cmd_locators(game, systems: list[str]) -> int:
    for sys_name in systems:
        name = f"game/space/systems/{sys_name}"
        _data, part = partition_or_none(game, name)
        print(f"=== {name}")
        if part is None:
            print("  <unreadable>")
            continue
        n = 0
        for inst, obj in part.instance_objects():
            if not isinstance(obj, dict):
                continue
            if "SystemDestinationLocator" not in str(obj.get("$", "")):
                continue
            n += 1
            print(f"  locator {inst.index}:")
            for k, v in obj.items():
                print(f"    {k:22s} {str(v)[:100]}")
        print(f"  {n} locator(s)")
    return 0


def cmd_jumpgraph(game) -> int:
    """Every JumpToSystem edge: which systems are targets, which are never a target."""
    prefix = "game/space/systems/systemdata/systemdata_"
    inst_to_system: dict[str, str] = {}
    systems = []
    for name in sorted(game.iter_names(prefix)):
        if not name.startswith(prefix) or "/" in name[len(prefix):]:
            continue
        sys_name = name[len(prefix):]
        systems.append(sys_name)
        _data, part = partition_or_none(game, name)
        if part is None:
            continue
        for inst in part.instances:
            if inst.guid:
                inst_to_system[inst.guid_text() if hasattr(inst, "guid_text") else
                                _guid_text(inst.guid)] = sys_name

    edges: dict[str, set[str]] = {}
    unresolved: dict[str, int] = {}
    for sys_name in systems:
        _data, part = partition_or_none(game, f"game/space/systems/{sys_name}")
        if part is None:
            continue
        targets: set[str] = set()
        for _inst, obj in part.instance_objects():
            if not isinstance(obj, dict):
                continue
            if "SystemDestinationLocator" not in str(obj.get("$", "")):
                continue
            jump = obj.get("JumpToSystem")
            refs = jump if isinstance(jump, list) else ([jump] if jump else [])
            for ref in refs:
                gid = ref.get("__import__") if isinstance(ref, dict) else None
                if not gid:
                    continue
                target = inst_to_system.get(str(gid))
                if target:
                    targets.add(target)
                else:
                    unresolved[str(gid)] = unresolved.get(str(gid), 0) + 1
        edges[sys_name] = targets

    print(f"{'from':14s} {'targets'}")
    for sys_name in systems:
        t = sorted(edges.get(sys_name, ()))
        print(f"{sys_name:14s} {len(t):2d}  {', '.join(t)}")

    inbound = {s: 0 for s in systems}
    for src, targets in edges.items():
        for t in targets:
            inbound[t] = inbound.get(t, 0) + 1
    print("\ninbound jump edges:")
    for s in systems:
        print(f"  {s:14s} {inbound.get(s, 0)}")
    never = [s for s in systems if inbound.get(s, 0) == 0]
    print(f"\nnever a jump target ({len(never)}): {', '.join(never) or 'none'}")
    print(f"total jump edges: {sum(len(t) for t in edges.values())} across {len(edges)} systems")
    print(f"unresolved jump import GUIDs: {len(unresolved)} "
          f"({sum(unresolved.values())} reference(s))")
    return 0


def _guid_text(raw: bytes) -> str:
    from frostbite.dbobject import Guid

    return Guid.from_le_fields(raw).text


def cmd_verify(game) -> int:
    """Cross-check: prefab condition flags == SystemData AvailableFlags == what unlock assets write."""
    prefix = "game/space/systems/systemdata/systemdata_"
    avail: dict[str, str] = {}
    for name in sorted(game.iter_names(prefix)):
        if not name.startswith(prefix) or "/" in name[len(prefix):]:
            continue
        _data, part = partition_or_none(game, name)
        obj = next((o for _i, o in part.instance_objects() if isinstance(o, dict)), {})
        g = (((obj.get("AvailableFlag") or {}).get("PlotFlagId") or {}).get("Guid"))
        avail[str(g).lower()] = name[len(prefix):]

    _data, prefab = partition_or_none(
        game, "game/ui/pausemenu/galaxymap/prefabs/spawnedgalaxymap")
    watched = set()
    for _inst, obj in prefab.instance_objects():
        if not isinstance(obj, dict) or "PlotConditionNotification" not in str(obj.get("$", "")):
            continue
        for cond in obj.get("PlotConditions") or []:
            ref = (cond.get("PlotFlagReference") or {}).get("PlotFlagId") or {}
            if ref.get("Guid") is not None:
                watched.add(str(ref["Guid"]).lower())

    unlock_prefix = "game/plots/systems/space/galaxymap_unlock_"
    written: set[str] = set()
    for name in game.iter_names(unlock_prefix):
        if not name.startswith(unlock_prefix):
            continue
        _d, part = partition_or_none(game, name)
        written.update(str(g).lower() for p, g in part.all_guids() if "PlotFlagId" in p)

    a, w = set(avail), watched
    print(f"SystemData AvailableFlags : {len(a)}")
    print(f"prefab watched flags      : {len(w)}")
    print(f"flags written by unlock_* : {len(written)}")
    print(f"prefab watches ALL AvailableFlags : {a <= w} (extra watched: {len(w - a)})")
    print(f"AvailableFlags written by unlock assets: {len(a & written)}/{len(a)}")
    print(f"  missing: {', '.join(sorted(avail[g] for g in a - written)) or '-'}")
    print(f"  extra flags written (not a system): {len(written - a)}")
    return 0


def cmd_refs(game, assets: list[str]) -> int:
    """Resolve an asset's imports to asset names (index over game/space/**)."""
    seen: dict[str, str] = {}
    scanned = 0
    for name in game.iter_names("game/space/"):
        if not name.startswith("game/space/"):
            continue
        _data, part = partition_or_none(game, name)
        scanned += 1
        if part is None or not hasattr(part, "guid"):
            continue
        seen.setdefault(part.guid.text, name)
    print(f"indexed {len(seen)} partitions from {scanned} game/space asset(s)")

    for asset in assets:
        _data, part = partition_or_none(game, asset)
        print(f"\n{asset}: {len(part.imports)} import(s), {len(part.instances)} instance(s)")
        resolved = {}
        for pg, ig in part.imports:
            resolved.setdefault(seen.get(pg.text, "?"), []).append(ig.text)
        for target, insts in sorted(resolved.items()):
            print(f"   {len(insts):3d}x {target}")
    return 0


def cmd_names(game) -> int:
    """Per system: the sun asset (display name), its planets and its landable destinations."""
    seen: dict[str, str] = {}
    scanned = 0
    for name in game.iter_names("game/space/"):
        if not name.startswith("game/space/"):
            continue
        _data, part = partition_or_none(game, name)
        scanned += 1
        if part is None or not hasattr(part, "guid"):
            continue
        seen.setdefault(part.guid.text, name)
    print(f"indexed {len(seen)} partitions from {scanned} game/space asset(s)\n")

    prefix = "game/space/systems/systemdata/systemdata_"
    systems = [n[len(prefix):] for n in game.iter_names(prefix)
               if n.startswith(prefix) and "/" not in n[len(prefix):]]
    print(f"{'system':14s} {'sun (name)':26s} {'planets':46s} destinations")
    for sys_name in sorted(systems):
        _data, part = partition_or_none(game, f"game/space/systems/{sys_name}")
        if part is None:
            print(f"{sys_name:14s} <unreadable>")
            continue
        targets = {seen.get(pg.text, "?") for pg, _ig in part.imports}
        suns = sorted(t.rsplit("/", 1)[-1].replace("spaceobject_sun_", "")
                      for t in targets if t.startswith("game/space/spaceobjects/sun/"))
        planets = sorted(t.rsplit("/", 1)[-1].replace("spaceobject_plt_", "")
                         for t in targets if "/spaceobjects/plt/" in t)
        named = [p for p in planets if not re.match(r"^(gas|ice|lun|des|met|ali|lav)_\d+$", p)]
        dests = sorted(t.rsplit("/", 1)[-1].replace("destination_plt_", "")
                       for t in targets if t.startswith("game/space/destinations/plt/"))
        print(f"{sys_name:14s} {','.join(suns):26s} {','.join(named):46s} "
              f"{','.join(dests)}")
    return 0


def main(argv: list[str]) -> int:
    game = vfs.Game()
    cmd = argv[0] if argv else "who"
    if cmd == "who":
        return cmd_who(game)
    if cmd == "rows":
        return cmd_rows(game)
    if cmd == "row":
        return cmd_row(game, argv[1:] or ["aya_01", "kadara_01"])
    if cmd == "part":
        return cmd_part(game, argv[1:])
    if cmd == "full":
        return cmd_full(game, argv[1:])
    if cmd == "avail":
        return cmd_avail(game)
    if cmd == "matrix":
        return cmd_matrix(game)
    if cmd == "unlock":
        return cmd_unlock(game)
    if cmd == "gate":
        return cmd_gate(game)
    if cmd == "verify":
        return cmd_verify(game)
    if cmd == "locators":
        return cmd_locators(game, argv[1:] or ["aya_01", "kadara_01"])
    if cmd == "jumpgraph":
        return cmd_jumpgraph(game)
    if cmd == "names":
        return cmd_names(game)
    if cmd == "refs":
        return cmd_refs(game, argv[1:])
    if cmd == "writers":
        return cmd_writers(game, argv[1:], ["game/plots/", "game/space/"])
    if cmd == "map":
        return cmd_map(game, argv[1:] or [
            "game/space/systems/",
            "game/ui/pausemenu/galaxymap/",
            "game/ui/galaxymap/",
            "game/plots/systems/",
        ])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
