"""Command line interface: ``ls``, ``find``, ``guid``, ``dump``, ``selftest``.

Run from the project root either as a module::

    python -m tools.frostbite ls --filter plotexpressions/hub_tempest

...or directly::

    python tools\\frostbite\\run.py ls --filter plotexpressions/hub_tempest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, compress, partition, vfs
from .dbobject import Guid

DEFAULT_SAVE = Path(__file__).resolve().parents[2] / "docs" / "Career870ee94.plot.json"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_save(path: Path | None) -> dict[str, set[str]] | None:
    """Return {kind: set(guid text)} for a ``*.plot.json`` save dump, or None."""
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        kind: set(values)
        for kind, values in doc.items()
        if isinstance(values, dict)
    }


def save_kinds(save: dict[str, set[str]] | None, text: str) -> list[str]:
    if not save:
        return []
    return [kind for kind, values in save.items() if text in values]


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _game(args) -> vfs.Game:
    return vfs.Game(args.game, roots=tuple(args.roots), use_cache=not args.no_cache)


# ---------------------------------------------------------------------------
# ls
# ---------------------------------------------------------------------------
def cmd_ls(args) -> int:
    game = _game(args)
    index = game.index()
    total = 0
    shown = 0
    limit = args.limit
    for name in game.iter_names(args.filter):
        records = index[name]
        root_filter = records
        if args.root != "all":
            root_filter = [r for r in records if r.root == args.root]
        if not root_filter:
            continue
        record = root_filter[0]
        total += 1
        if limit and shown >= limit:
            continue
        if args.unique:
            print(f"{record.name}\t{record.sha1.hex()}\t{record.size}")
        else:
            print(
                f"{record.name}\t{record.sha1.hex()}\t{record.size}\t"
                f"{record.original_size}\t{record.sb_path}"
            )
        shown += 1

    print(
        f"# {_fmt_int(total)} name(s) matched"
        + (f", showing {_fmt_int(shown)}" if limit and total > shown else "")
        + f"; index built from {_fmt_int(game.stats.get('sb_files', 0))} superbundle(s)"
        + f", {_fmt_int(game.stats.get('names', 0))} unique names"
        + (f" [cache hit]" if game.stats.get("cache") else ""),
        file=sys.stderr,
    )
    return 0


# ---------------------------------------------------------------------------
# find
# ---------------------------------------------------------------------------
def cmd_find(args) -> int:
    game = _game(args)
    records = game.find(args.name)
    if not records:
        print(f"NOT FOUND: {args.name}", file=sys.stderr)
        suggestions = [n for n in game.iter_names(args.name.split("/")[-1].lower())][:10]
        if suggestions:
            print("did you mean:", file=sys.stderr)
            for s in suggestions:
                print("  " + s, file=sys.stderr)
        return 2

    print(f"asset    {records[0].name}")
    print(f"listings {len(records)} (highest priority first)")
    shown = records if args.all else records[:3]
    for i, rec in enumerate(shown):
        mark = "*" if i == 0 else " "
        print(
            f" {mark} {rec.sb_path}\n"
            f"     bundle={rec.bundle} kind={rec.kind} root={rec.root}\n"
            f"     sha1={rec.sha1.hex()} size={rec.size} originalSize={rec.original_size}"
        )
    if len(records) > len(shown):
        print(f"   ... {len(records) - len(shown)} more listing(s) "
              f"(same sha1 = cas-level dedup); use --all to show them")
        distinct = {r.sha1 for r in records}
        print(f"   distinct sha1 among listings: {len(distinct)}")

    record = records[0]
    if args.alldistinct:
        print("distinct variants:")
        seen = set()
        for rec in records:
            if rec.sha1 in seen:
                continue
            seen.add(rec.sha1)
            print(f"   {rec.sha1.hex()} size={rec.size} originalSize={rec.original_size} "
                  f"{rec.sb_path}")

    if args.no_chunk:
        return 0
    try:
        hit = game.locate(record)
    except vfs.AssetError as exc:
        print(f"chunk     UNRESOLVED: {exc}", file=sys.stderr)
        return 3

    print(f"chunk     kind={hit['kind']}")
    if hit["cas"]:
        print(f"          cas={hit['cas']}")
        print(f"          offset=0x{hit['offset']:X} ({hit['offset']}) size={hit['size']}")
        print(f"          catalog={hit['catalog'].path}")
    if args.data:
        try:
            data, location = game.chunk_data(record)
            print(f"          decompressed={len(data)} bytes, {len(location['blocks'])} block(s)")
        except vfs.AssetError as exc:
            print(f"          decompression failed: {exc}")
    return 0


# ---------------------------------------------------------------------------
# guid
# ---------------------------------------------------------------------------
def cmd_guid(args) -> int:
    game = _game(args)
    save = None if args.no_save else load_save(Path(args.save) if args.save else DEFAULT_SAVE)

    try:
        records = game.find(args.name)
        if not records:
            raise vfs.AssetError(f"asset not found in any superbundle: {args.name}")
    except vfs.AssetError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2

    # try each listing, highest priority first, until one parses as a partition
    last_error = None
    result = None
    for record in records[: args.tries]:
        try:
            part = game.partition(record)
        except vfs.AssetError as exc:
            last_error = exc
            continue
        result = (record, part)
        break

    if result is None:
        print(f"FAILED: no readable EBX partition for {args.name}", file=sys.stderr)
        if last_error:
            print(f"  last error: {last_error}", file=sys.stderr)
        return 3

    record, part = result
    location = getattr(part, "location", {})
    embedded_name = None
    for _inst, obj in part.instance_objects():
        if isinstance(obj, dict) and isinstance(obj.get("Name"), str) and "/" in obj["Name"]:
            embedded_name = obj["Name"]
            break

    flag_guids = []
    other_guids = []
    for path, guid in part.all_guids():
        if "PlotFlagId" in path:
            flag_guids.append((path, guid))
        else:
            other_guids.append((path, guid))

    if args.json:
        payload = {
            "requested": args.name,
            "asset": record.name,
            "superbundle": record.sb_path,
            "bundle": record.bundle,
            "kind": record.kind,
            "sha1": record.sha1.hex(),
            "size": record.size,
            "original_size": record.original_size,
            "cas": str(location.get("cas")) if location.get("cas") else None,
            "cas_offset": location.get("offset"),
            "partition_guid": part.guid.text,
            "partition_guid_raw": part.guid.hex,
            "embedded_name": embedded_name,
            "embedded_name_matches": (embedded_name or "").lower() == record.name.lower(),
            "flag_guids": [
                {"path": p, "guid": g.text, "raw": g.hex, "save_kinds": save_kinds(save, g.text)}
                for p, g in flag_guids
            ],
            "other_guids": [
                {"path": p, "guid": g.text, "raw": g.hex} for p, g in other_guids
            ],
            "counts": {
                "instances": len(part.instances),
                "types": len(part.types),
                "fields": len(part.fields),
                "imports": len(part.imports),
                "arrays": len(part.arrays),
            },
        }
        print(json.dumps(payload, indent=2))
        return 0

    blocks = location.get("blocks") or []
    block_desc = ", ".join(f"{b.type_name}:{b.compressed_size}->{b.uncompressed_size}"
                           for b in blocks) or "stored uncompressed"

    print(f"asset        {record.name}")
    print(f"listing      {record.sb_path}")
    print(f"bundle       {record.bundle} [{record.kind}]")
    print(f"sha1         {record.sha1.hex()}")
    print(f"cas          {Path(location['cas']).name if location.get('cas') else '?'}"
          f" @0x{location.get('offset', 0):X} ({location.get('size', 0)} bytes) "
          f"-> {record.original_size} bytes [{block_desc}]")
    print(f"partition    magic 0x{partition.MAGIC:08X}, {len(part.instances)} instance(s), "
          f"{len(part.types)} type(s), {len(part.fields)} field(s), "
          f"{len(part.arrays)} array(s), {len(part.imports)} import(s)")
    if embedded_name is not None:
        ok = embedded_name.lower() == record.name.lower()
        print(f"embedded     Asset.Name = {embedded_name}  "
              f"[{'matches requested path' if ok else 'DIFFERS from requested path'}]")
    else:
        print("embedded     this asset has no Asset.Name field")

    print(f"partition-guid {part.guid.text}   (header offset 0x28; not a save key)")
    if flag_guids:
        print(f"flag-guid(s)  {len(flag_guids)} PlotFlagId.Guid value(s):")
        for path, guid in flag_guids:
            kinds = save_kinds(save, guid.text)
            tag = f"save:{'/'.join(kinds)}" if kinds else ("save:absent" if save else "no save loaded")
            print(f"  {guid.text}  raw={guid.hex}  [{tag}]  {path}")
    else:
        print("flag-guid(s)  none (this asset contains no PlotFlagId)")

    if other_guids:
        print(f"other-guid(s) {len(other_guids)}:")
        for path, guid in other_guids:
            print(f"  {guid.text}  [{path}]")

    primary = None
    if flag_guids:
        primary = flag_guids[0][1]
        if len(flag_guids) > 1:
            print(f"NOTE          this asset references {len(flag_guids)} plot flags; "
                  f"it has no single 16-byte GUID of its own (MEA assets are named, "
                  f"not GUID-keyed).  The save-file join is the flag list above.")
    print()
    if primary is not None:
        print(f"GUID          {primary.text}")
        print(f"RAW           {primary.hex}")
    else:
        print(f"GUID          (none - only the non-persistent partition GUID "
              f"{part.guid.text})")
    if save:
        hits = sum(1 for _p, g in flag_guids if save_kinds(save, g.text))
        print(f"SAVE-JOIN     {hits}/{len(flag_guids)} flag GUID(s) found in the save dump")
    return 0


# ---------------------------------------------------------------------------
# dump
# ---------------------------------------------------------------------------
def cmd_dump(args) -> int:
    game = _game(args)
    import hashlib

    records = game.find(args.name)
    if not records:
        print(f"FAILED: asset not found: {args.name}", file=sys.stderr)
        return 2
    last_error = None
    for record in records[: args.tries]:
        try:
            data, location = game.chunk_data(record)
            break
        except vfs.AssetError as exc:
            last_error = exc
    else:
        print(f"FAILED: {last_error}", file=sys.stderr)
        return 3

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"asset        {record.name}")
    print(f"sha1         {record.sha1.hex()}")
    print(f"cas          {Path(location['cas']).name} @0x{location['offset']:X} "
          f"({location['size']} bytes)")
    print(f"wrote        {out} ({len(data)} bytes, sha1 {hashlib.sha1(data).hexdigest()})")
    if args.partition:
        try:
            part = partition.Partition(data)
            for line in part.describe():
                print("  " + line)
        except partition.PartitionError as exc:
            print(f"  (not an EBX partition: {exc})")
    return 0


# ---------------------------------------------------------------------------
# join
# ---------------------------------------------------------------------------
def cmd_join(args) -> int:
    """Resolve a whole name list to plot-flag GUIDs (the actual project need)."""
    game = _game(args)
    save = None if args.no_save else load_save(Path(args.save) if args.save else DEFAULT_SAVE)
    names_path = Path(args.names)
    if not names_path.is_file():
        print(f"FAILED: name list not found: {names_path}", file=sys.stderr)
        return 2

    names = []
    for line in names_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    if args.limit:
        names = names[: args.limit]

    results = []
    stats = {
        "names": len(names),
        "found": 0,
        "parsed": 0,
        "with_flags": 0,
        "no_flags": 0,
        "failed": 0,
    }
    guid_to_names: dict[str, list[str]] = {}
    save_hits: set[str] = set()

    for i, name in enumerate(names, 1):
        entry = {"name": name, "flags": []}
        records = game.find(name)
        if not records:
            entry["status"] = "not-found"
            stats["failed"] += 1
            results.append(entry)
        else:
            stats["found"] += 1
            part = None
            used = None
            error = None
            for record in records[: args.tries]:
                try:
                    part = game.partition(record)
                    used = record
                    break
                except vfs.AssetError as exc:
                    error = str(exc)
            if part is None:
                entry["status"] = "unreadable"
                entry["error"] = error
                stats["failed"] += 1
            else:
                stats["parsed"] += 1
                entry["sha1"] = used.sha1.hex()
                entry["superbundle"] = used.sb_path
                entry["partition_guid"] = part.guid.text
                flags = [(p, g) for p, g in part.all_guids() if "PlotFlagId" in p]
                if flags:
                    stats["with_flags"] += 1
                    entry["status"] = "ok"
                else:
                    stats["no_flags"] += 1
                    entry["status"] = "no-flags"
                for path, guid in flags:
                    kinds = save_kinds(save, guid.text)
                    entry["flags"].append(
                        {"guid": guid.text, "path": path, "save_kinds": kinds}
                    )
                    guid_to_names.setdefault(guid.text, []).append(name)
                    if kinds:
                        save_hits.add(guid.text)
                results.append(entry)
        if args.progress and i % args.progress == 0:
            print(f"  ... {i}/{len(names)} names, {len(guid_to_names)} distinct flag GUIDs",
                  file=sys.stderr, flush=True)

    payload = {
        "names_file": str(names_path),
        "save_file": str(args.save or DEFAULT_SAVE) if save else None,
        "stats": {
            **stats,
            "distinct_flag_guids": len(guid_to_names),
            "distinct_flag_guids_in_save": len(save_hits),
        },
        "assets": results,
        "guid_to_names": guid_to_names,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    print(f"names read          {stats['names']:,}")
    print(f"found in a bundle   {stats['found']:,}")
    print(f"partition parsed    {stats['parsed']:,}")
    print(f"  with flags        {stats['with_flags']:,}")
    print(f"  without flags     {stats['no_flags']:,}")
    print(f"failed/unreadable   {stats['failed']:,}")
    print(f"distinct flag GUIDs {len(guid_to_names):,}"
          + (f", {len(save_hits):,} of them are save keys" if save else ""))
    print(f"wrote               {out}")
    return 0


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------
def _hx(data: bytes, limit: int | None = None) -> str:
    chunk = data[:limit] if limit else data
    return " ".join(f"{b:02x}" for b in chunk)


def cmd_evidence(args) -> int:
    """Print the byte-level facts the format documentation quotes."""
    from . import catalog as catalog_mod
    from . import dbobject, filelayer

    game = _game(args)
    root = game.root

    print("=" * 78)
    print("1. superbundle (.sb) has no file layer - it starts with a DbObject tag")
    print("=" * 78)
    sb_path = None
    for candidate in game._sb_files():
        if candidate.name.lower() == "anchorchannels.sb":
            sb_path = candidate
            break
    if sb_path is None and game._sb_files():
        sb_path = game._sb_files()[0]
    if sb_path:
        raw = sb_path.read_bytes()
        obj = dbobject.parse(raw)
        reader = dbobject.Reader(raw)
        root_tag = reader.u8()
        root_len = reader.packed_uint()
        body_start = reader.pos
        prop_tag = reader.u8()
        prop_name = reader.cstring()
        print(f"file        {sb_path.relative_to(root)}  ({len(raw)} bytes)")
        print(f"first 32    {_hx(raw, 32)}")
        print(f"decode      {root_tag:02x} = tag(Object,flags={root_tag >> 5}); "
              f"packed varint -> root object length {root_len}")
        print(f"            {prop_tag:02x} = tag(Array); property name {prop_name!r} "
              f"(NUL-terminated)")
        print(f"            then the array length varint; each element is "
              f"82 <varint length> = an Object")
        print(f"object end  body starts at 0x{body_start:X}, length {root_len}, "
              f"file {len(raw)} bytes -> ends exactly at EOF "
              f"[{body_start + root_len == len(raw)}]")
        print(f"parsed      root keys={list(obj)}; "
              f"{len(obj.get('bundles') or [])} bundle(s) in this file")

    print()
    print("=" * 78)
    print("2. table of contents (.toc) = Ooa obfuscation -> DiCE signature -> DbObject")
    print("=" * 78)
    toc_paths = sorted(root.rglob("*.toc"))
    if toc_paths:
        toc_path = toc_paths[0]
        raw = toc_path.read_bytes()
        info = filelayer.ooa_setup(raw)
        body = filelayer.ooa_deobfuscate(raw)
        stripped, layers = filelayer.strip(raw)
        print(f"file        {toc_path.relative_to(root)}  ({len(raw)} bytes)")
        print(f"last 36     {_hx(raw[-36:])}")
        print(f"            {filelayer.OOA_SIGNATURE.decode()!r}")
        print(f"setupLength {info['setup_length']}  (little-endian int32 at "
              f"fileSize-36)")
        print(f"decrypted   version={info['version']} mode={info['mode']} "
              f"seed={info['seed']} plaintextSize={info['file_size']}")
        print(f"check       plaintextSize {info['file_size']} + setupLength "
              f"{info['setup_length']} == fileSize {len(raw)}  "
              f"[{info['file_size'] + info['setup_length'] == len(raw)}]")
        print(f"after Ooa   {len(body)} bytes, first 16 {_hx(body, 16)}")
        print("            -> 00 d1 ce 01 = 0x01CED100 = DiCE *signature* layer")
        print(f"after DiCE  {len(stripped)} bytes (8 + 548 byte header skipped), "
              f"first 16 {_hx(stripped, 16)}")
        print(f"layers seen {layers} (plus the DiCE layer removed inside)")
        print(f"parsed      {list(dbobject.parse(stripped))}")

    print()
    print("=" * 78)
    print("3. cas.cat = DiCE signature -> 'NyanNyan' catalog")
    print("=" * 78)
    cat_paths = sorted(root.rglob("cas.cat"))
    if cat_paths:
        raw = cat_paths[0].read_bytes()
        data, layers = filelayer.strip(raw)
        print(f"file        {cat_paths[0].relative_to(root)}  ({len(raw)} bytes)")
        print(f"first 16    {_hx(raw, 16)}  -> DiCE signature, layers={layers}")
        print(f"stripped    {len(data)} bytes, first 16 {_hx(data, 16)}")
        print("            'NyanNyan' as two little-endian uint64 = "
              "0x6E61794E6E61794E")
        counts = [int.from_bytes(data[16 + 4 * i:20 + 4 * i], "little") for i in range(3)]
        print(f"counts      normal={counts[0]:,} patch={counts[1]:,} "
              f"encrypted={counts[2]:,}; entries start at 0x28, 36 bytes each")

    print()
    print("=" * 78)
    print("4. chunk in .cas = big-endian block header(s) + zstd")
    print("=" * 78)
    print(f"asset       {args.name}")
    try:
        record = game.resolve(args.name)
    except vfs.AssetError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2
    raw, location = game.chunk_data(record)
    data, _ = game.chunk_data(record)
    hit = game.locate(record)
    cas_raw = hit["catalog"].read_chunk(hit["entry"])
    print(f"sha1        {record.sha1.hex()}  size={record.size} "
          f"originalSize={record.original_size}")
    print(f"cas         {Path(hit['cas']).name} @0x{hit['offset']:X} ({hit['size']} bytes)")
    print(f"first 24    {_hx(cas_raw, 24)}")
    if record.size != record.original_size:
        header = compress.read_block_header(cas_raw, 0)
        print(f"block 0     uncompressedSize={header.uncompressed_size} "
              f"(00 00 05 60 = 1376)")
        print(f"            flags=0x{header.raw_flags:08X}: type=0x{header.compression_type:02X} "
              f"({header.type_name}), compressionFlags=0x{header.compression_flags:X}, "
              f"compressedSize=0x{header.compressed_size:X} ({header.compressed_size})")
        print(f"decompressed {len(raw)} bytes == originalSize "
              f"[{len(raw) == record.original_size}]")
    else:
        print(f"stored uncompressed: {len(raw)} bytes")

    print()
    print("=" * 78)
    print("5. decompressed chunk = EBX partition; GUID at header offset 0x28")
    print("=" * 78)
    part = partition.Partition(raw)
    head = raw[:64]
    fields = [
        ("magic", 0, 4), ("headerSize", 4, 4), ("dataSize", 8, 4),
        ("importCount", 12, 4), ("instanceCount", 16, 2),
        ("namedInstanceCount", 18, 2), ("exportedInstanceCount", 20, 2),
        ("typeDefinitionCount", 22, 2), ("fieldDefinitionCount", 24, 2),
        ("nameTableSize", 26, 2), ("stringTableSize", 28, 4),
        ("arrayCount", 32, 4), ("arrayOffset", 36, 4), ("guid", 40, 16),
    ]
    for label, off, size in fields:
        value = int.from_bytes(head[off:off + size], "little")
        print(f"  +0x{off:02X} {label:<20} {_hx(head[off:off+size]):<48} "
              f"{value if size != 16 else ''}")
    print(f"header invariant: 64 + imports*32 + names + fields*16 + types*16 + "
          f"align(instances*4,16) + align(arrays*12,16)")
    print(f"                = 64 + 384 + {len(part.fields)}*16 + {len(part.types)}*16 "
          f"+ 16 + 32 = {part.header_size} == declared headerSize "
          f"[{part.header_size == 64 + 384 + len(part.fields)*16 + len(part.types)*16 + 16 + 32}]")
    print(f"partition GUID  {part.guid.text}  (bytes {_hx(raw[40:56])})")
    print(f"instances       {len(part.instances)}; types {len(part.types)}; "
          f"fields {len(part.fields)}; arrays {len(part.arrays)}")
    for inst, obj in part.instance_objects():
        name = obj.get("Name") if isinstance(obj, dict) else None
        print(f"  instance type={part.types[inst.type_index].label:<30} "
              f"guid={inst.guid.hex() if inst.guid else '-':<34} "
              f"{'Name=' + name if isinstance(name, str) else ''}")
    print()
    print("GUID byte order: asset data stores .NET raw order (data1/2/3 "
          "little-endian),")
    print("a DbObject Guid field stores big-endian fields. Both render the same text.")
    for path, guid in part.all_guids():
        print(f"  {guid.text}  raw={guid.hex}  {path}")
    return 0


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------
def cmd_info(args) -> int:
    game = _game(args)
    try:
        cats = game.catalogs()
    except vfs.AssetError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 3
    sb_files = game._sb_files()
    print(f"game root     {game.root}")
    print(f"superbundles  {len(sb_files)} .sb file(s) under {', '.join(game.roots)}")
    print(f"catalogs      {len(cats.catalogs)} cas.cat file(s), "
          f"{_fmt_int(cats.total_entries)} unique chunk sha1(s)")
    tocs = list(game.root.rglob("*.toc"))
    print(f"toc files     {len(tocs)}")
    zstd = compress.zstd_backend_name()
    print(f"zstd backend  {zstd}")
    if DEFAULT_SAVE.is_file():
        save = load_save(DEFAULT_SAVE)
        total = len(set().union(*save.values())) if save else 0
        print(f"save dump     {DEFAULT_SAVE} ({_fmt_int(total)} flag GUIDs)")
    return 0


# ---------------------------------------------------------------------------
# build-parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    # options accepted both before and after the subcommand; the subcommand
    # copies use SUPPRESS so an absent value does not clobber the global one
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--game", default=argparse.SUPPRESS,
                        help="game install root")
    common.add_argument("--roots", nargs="+", default=argparse.SUPPRESS,
                        choices=["data", "patch", "update"],
                        help="which layouts to search")
    common.add_argument("--no-cache", action="store_true", default=argparse.SUPPRESS,
                        help="do not read/write the superbundle index cache")

    parser = argparse.ArgumentParser(
        prog="frostbite",
        description="Read Mass Effect Andromeda's Frostbite container and resolve "
                    "asset names to plot-flag GUIDs.",
    )
    parser.add_argument("--game", default=str(vfs.DEFAULT_GAME_ROOT),
                        help="game install root (default: %(default)s)")
    parser.add_argument("--roots", nargs="+", default=["patch", "update", "data"],
                        choices=["data", "patch", "update"],
                        help="which layouts to search (default: patch update data)")
    parser.add_argument("--no-cache", action="store_true",
                        help="do not read/write the superbundle index cache")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ls", parents=[common], help="list asset names with sha1 and size")
    p.add_argument("--filter", "-f", default=None, help="only names containing this substring")
    p.add_argument("--root", default="all", choices=["all", "data", "patch", "update"],
                   help="restrict to one layout (default: all)")
    p.add_argument("--limit", type=int, default=100,
                   help="max rows to print (0 = unlimited, default 100)")
    p.add_argument("--unique", action="store_true", help="omit originalSize and superbundle columns")
    p.set_defaults(func=cmd_ls)

    p = sub.add_parser("find", parents=[common], help="locate one asset")
    p.add_argument("name")
    p.add_argument("--all", action="store_true", help="print every superbundle listing")
    p.add_argument("--alldistinct", action="store_true",
                   help="summarise the distinct sha1 variants")
    p.add_argument("--no-chunk", action="store_true", help="skip cas resolution")
    p.add_argument("--data", action="store_true",
                   help="also read and decompress the chunk")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("guid", parents=[common],
                       help="print the asset's GUID(s) in .NET text form")
    p.add_argument("name")
    p.add_argument("--save", default=None,
                   help=f"save dump to annotate against (default: {DEFAULT_SAVE})")
    p.add_argument("--no-save", action="store_true", help="skip save annotation")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--tries", type=int, default=8,
                   help="how many superbundle listings to try (default 8)")
    p.set_defaults(func=cmd_guid)

    p = sub.add_parser("dump", parents=[common],
                       help="write the decompressed asset bytes to a file")
    p.add_argument("name")
    p.add_argument("--out", "-o", required=True)
    p.add_argument("--partition", action="store_true", help="also print partition details")
    p.add_argument("--tries", type=int, default=8)
    p.set_defaults(func=cmd_dump)

    p = sub.add_parser("info", parents=[common],
                       help="show install/catalog/backend overview")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("evidence", parents=[common],
                       help="print the byte-level format evidence that the docs quote")
    p.add_argument("name", nargs="?", default=(
        "game/plots/levels/hubs/hub_tempest/plotexpressions/"
        "crit_tempest_0725_meridian_returntocity_available"),
        help="asset to demonstrate with")
    p.set_defaults(func=cmd_evidence)

    p = sub.add_parser("join", parents=[common],
                       help="resolve a whole name list (one per line) to flag GUIDs")
    p.add_argument("--names", required=True, help="text file with one asset name per line")
    p.add_argument("--save", default=None, help="save dump for annotation")
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--out", "-o", required=True, help="output JSON path")
    p.add_argument("--limit", type=int, default=0, help="only the first N names")
    p.add_argument("--tries", type=int, default=4,
                   help="listings to try per name (default 4)")
    p.add_argument("--progress", type=int, default=200,
                   help="print progress every N names (0 = quiet)")
    p.set_defaults(func=cmd_join)

    p = sub.add_parser("selftest", parents=[common],
                       help="prove the container parsing is correct")
    p.set_defaults(func=cmd_selftest)
    return parser


def cmd_selftest(args) -> int:
    from .selftest import main as selftest_main
    return selftest_main(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
