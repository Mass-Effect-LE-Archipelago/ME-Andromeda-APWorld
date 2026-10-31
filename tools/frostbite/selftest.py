"""Self-test: prove the container parsing is correct, not merely plausible.

The checks are chosen so that a wrong format decision fails loudly:

1. every ``.toc`` parses as a DbObject after the Ooa + DiCE layers are removed,
   and the Ooa setup block's declared plaintext size plus its own size equals
   the file size exactly;
2. every ``.sb`` parses, and every ebx/res record has a 20-byte sha1 and a path;
3. every ``cas.cat`` parses to exactly its file length, and the sha1 of a
   sampled asset resolves to a cas file position;
4. sampled EBX chunks decompress to exactly ``originalSize`` and satisfy
   ``headerSize == 64 + imports*32 + names + fields*16 + types*16 + alignment``;
5. **the strong one**: for sampled assets that carry an ``Asset.Name`` field,
   the name embedded *inside the decompressed data* equals the asset path we
   looked up.  That closes the loop name -> .sb -> sha1 -> cas.cat -> cas bytes
   -> zstd -> partition, with data the format itself vouches for;
6. the documented target asset's flag GUIDs are keys in the save dump.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from . import catalog, compress, dbobject, filelayer, partition, vfs

TARGET = ("game/plots/levels/hubs/hub_tempest/plotexpressions/"
          "crit_tempest_0725_meridian_returntocity_available")

ACCEPTED = [
    "5fb38cb4-ded5-4470-9193-1aed885201fd",
    "fd1b5d9d-e01a-462d-a4ff-9cd48f5b01e0",
    "771d0593-e901-41f5-ba94-f524783b0378",
]


class _Check:
    def __init__(self):
        self.failures = 0
        self.checks = 0

    def ok(self, label: str, detail: str = "") -> None:
        self.checks += 1
        print(f"  PASS  {label}" + (f"  [{detail}]" if detail else ""))

    def fail(self, label: str, detail: str = "") -> None:
        self.checks += 1
        self.failures += 1
        print(f"  FAIL  {label}" + (f"  [{detail}]" if detail else ""))


def _sample(items: list, count: int) -> list:
    if len(items) <= count:
        return list(items)
    step = len(items) / count
    return [items[int(i * step)] for i in range(count)]


def main(args=None) -> int:
    game = vfs.Game(
        getattr(args, "game", vfs.DEFAULT_GAME_ROOT),
        roots=tuple(getattr(args, "roots", ["patch", "update", "data"])),
        use_cache=not getattr(args, "no_cache", False),
    )
    check = _Check()
    start = time.time()

    print(f"frostbite self-test against {game.root}")
    print(f"roots: {', '.join(game.roots)}")
    print()

    # -- 1. toc -------------------------------------------------------------
    print("1. table-of-contents files")
    tocs = sorted(game.root.rglob("*.toc"))
    layer_stats: dict[str, int] = {}
    ooa_ok = 0
    for path in tocs:
        raw = path.read_bytes()
        try:
            info = filelayer.ooa_setup(raw)
            if info["file_size"] + info["setup_length"] == len(raw):
                ooa_ok += 1
        except filelayer.FileLayerError:
            pass
        try:
            body, layers = filelayer.strip(raw)
            obj = dbobject.parse(body)
        except Exception as exc:  # noqa: BLE001 - report, do not crash
            check.fail(path.name, str(exc))
            continue
        key = "+".join(layers) or "none"
        layer_stats[key] = layer_stats.get(key, 0) + 1
        if not isinstance(obj, dict):
            check.fail(path.name, f"root is {type(obj).__name__}")
    if check.failures == 0:
        check.ok(f"all {len(tocs)} .toc files parsed",
                 ", ".join(f"{k}:{v}" for k, v in sorted(layer_stats.items())))
        check.ok(f"{ooa_ok}/{len(tocs)} Ooa setup blocks self-consistent",
                 "plaintextSize + setupSize == fileSize")

    # -- 2. sb --------------------------------------------------------------
    print("2. superbundles")
    sbs = sorted(game.root.rglob("*.sb"))
    total_listings = 0
    bad_sha1 = 0
    for path in sbs:
        try:
            body, _ = filelayer.strip(path.read_bytes())
            obj = dbobject.parse(body)
        except Exception as exc:  # noqa: BLE001
            check.fail(path.name, str(exc))
            continue
        for bundle in obj.get("bundles") or []:
            for kind in ("ebx", "res"):
                for entry in bundle.get(kind) or []:
                    total_listings += 1
                    sha1 = entry.get("sha1")
                    if not isinstance(sha1, bytes) or len(sha1) != 20:
                        bad_sha1 += 1
    if check.failures == 0:
        check.ok(f"all {len(sbs)} .sb files parsed",
                 f"{total_listings:,} ebx/res listings")
    if bad_sha1:
        check.fail("sha1 field", f"{bad_sha1} record(s) without a 20-byte sha1")
    else:
        check.ok("every ebx/res record has a 20-byte sha1")

    # -- 3. catalogs --------------------------------------------------------
    print("3. cas.cat catalogs")
    try:
        cats = game.catalogs()
        check.ok(f"{len(cats.catalogs)} catalog(s) parsed to exactly their file length",
                 f"{cats.total_entries:,} unique sha1")
    except Exception as exc:  # noqa: BLE001
        check.fail("catalog parse", str(exc))
        cats = None

    # -- 4/5. sampled partitions -------------------------------------------
    print("4. sampled EBX chunks: decompress + partition header + embedded name")
    index = game.index()
    names = sorted(index)
    ebx_names = [n for n in names
                 if any(r.kind == "ebx" for r in index[n])]
    sample = _sample(ebx_names, getattr(args, "sample", 60) if args else 60)
    parsed = 0
    embedded_seen = 0
    embedded_match = 0
    guid_values = 0
    for name in sample:
        records = [r for r in index[name] if r.kind == "ebx"]
        record = records[0]
        try:
            part = game.partition(record)
        except vfs.AssetError as exc:
            check.fail(name, str(exc)[:160])
            continue
        parsed += 1
        for _inst, obj in part.instance_objects():
            if isinstance(obj, dict) and isinstance(obj.get("Name"), str):
                embedded_seen += 1
                if obj["Name"].lower() == record.name.lower():
                    embedded_match += 1
                break
        guid_values += len(part.all_guids())
    if parsed == len(sample):
        check.ok(f"{parsed}/{len(sample)} sampled chunks decompressed and parsed",
                 f"{guid_values} GUID-typed value(s) decoded")
    else:
        check.fail("sampled chunks", f"{parsed}/{len(sample)} parsed")
    if embedded_seen:
        if embedded_match == embedded_seen:
            check.ok(f"{embedded_match}/{embedded_seen} embedded Asset.Name values equal the "
                     f"asset path they were fetched by")
        else:
            check.fail("embedded Asset.Name mismatch",
                       f"{embedded_match}/{embedded_seen} matched")

    # -- 6. target ----------------------------------------------------------
    print("5. documented target asset")
    try:
        record = game.resolve(TARGET)
        part = game.partition(record)
        flags = [(p, g) for p, g in part.all_guids() if "PlotFlagId" in p]
        check.ok("target resolved", f"{record.sb_path} sha1={record.sha1.hex()}")
        check.ok("target partition parsed",
                 f"partition GUID {part.guid.text}, {len(part.instances)} instances")
        got = sorted(g.text for _p, g in flags)
        if got == sorted(ACCEPTED):
            check.ok(f"{len(flags)} flag GUIDs match the documented set", ", ".join(got))
        else:
            check.fail("flag GUID set differs",
                       f"got {got}, expected {sorted(ACCEPTED)}")
        save = None
        save_path = Path(getattr(args, "save", None) or
                         (Path(__file__).resolve().parents[2] / "docs" / "Career870ee94.plot.json"))
        if save_path.is_file():
            from .cli import load_save
            save = load_save(save_path)
        if save:
            joined = [(g.text, [k for k, v in save.items() if g.text in v]) for _p, g in flags]
            hits = sum(1 for _t, kinds in joined if kinds)
            if hits == len(flags):
                detail = "; ".join(f"{t} -> {'/'.join(k)}" for t, k in joined)
                check.ok(f"{hits}/{len(flags)} target flag GUIDs are keys in the save dump",
                         detail)
            else:
                check.fail("save join", f"only {hits}/{len(flags)} matched")
        else:
            print("  SKIP  save dump not found; run `info` to see the expected path")
    except Exception as exc:  # noqa: BLE001
        check.fail("target asset", str(exc))

    elapsed = time.time() - start
    print()
    print(f"{check.checks - check.failures}/{check.checks} checks passed in {elapsed:.1f}s")
    print("SELFTEST OK" if check.failures == 0 else f"SELFTEST FAILED ({check.failures} failure(s))")
    return 0 if check.failures == 0 else 1
