"""Parse Mass Effect Andromeda `.fbmod` files for the launcher's mod manager.

Two container generations exist in the owner's pack:

* **FBMODV2** — a Frostbite DbObject: `magic`, `gameProfile`, `gameVersion`, `title`, `author`,
  `category`, `version`, `description`, `icon`, `screenshots[]`, `resources[]`, `actions[]`.
  Resources carry the EBX asset path (`name`), a type (`ebx`/`embedded`), an archive index and
  offset/sizes; actions point a resource at a target bundle.
* **FROSTY** (v1) — older binary header: profile name, then title/author/category/version and a
  description, followed by the payload. Metadata is read heuristically; asset paths and target
  bundles are recovered as plaintext strings.

Both give us what a mod manager needs: what each mod replaces, and therefore where two mods
collide.

Usage:
  python fbmod.py list <mods-dir> [--json OUT]
  python fbmod.py show <file.fbmod>
  python fbmod.py conflicts <mods-dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frostbite import dbobject  # noqa: E402

ASSET_RE = re.compile(rb"(?:^|[\x00\x01-\x1f])((?:game|dev)/[A-Za-z0-9_./()\-]{4,150})")
BUNDLE_RE = re.compile(rb"(win32/[A-Za-z0-9_./()\-]{4,150})")
META_ORDER = ("title", "author", "category", "version", "description")


def _cstrings(data: bytes, start: int = 0, limit: int = 12) -> list[str]:
    out: list[str] = []
    i = start
    while i < len(data) and len(out) < limit:
        end = data.find(b"\x00", i)
        if end < 0 or end - i > 4000:
            break
        chunk = data[i:end]
        if chunk and all(32 <= c < 127 or c in (9, 10, 13) for c in chunk):
            out.append(chunk.decode("latin-1"))
            i = end + 1
        else:
            i += 1
    return out


def parse_v2(data: bytes) -> dict:
    obj = dbobject.parse(data)
    resources = []
    for res in obj.get("resources", []):
        resources.append({
            "name": res.get("name"),
            "type": res.get("type"),
            "archive_index": res.get("archiveIndex"),
            "offset": res.get("archiveOffset"),
            "compressed_size": res.get("compressedSize"),
            "uncompressed_size": res.get("uncompressedSize"),
        })
    actions = []
    for act in obj.get("actions", []):
        actions.append({"resource_id": act.get("resourceId"), "type": act.get("type"),
                        "bundle": act.get("bundle")})
    return {
        "format": "FBMODV2",
        "magic": obj.get("magic"),
        "profile": obj.get("gameProfile"),
        "title": obj.get("title"),
        "author": obj.get("author"),
        "category": obj.get("category"),
        "version": obj.get("version"),
        "description": obj.get("description"),
        "resources": resources,
        "actions": actions,
        "assets": sorted({r["name"] for r in resources if r.get("type") == "ebx" and r.get("name")}),
        "bundles": sorted({a["bundle"] for a in actions if a.get("bundle")}),
    }


def parse_v1(data: bytes) -> dict:
    profile = "MassEffectAndromeda"
    idx = data.find(profile.encode())
    meta: dict[str, str | None] = dict.fromkeys(META_ORDER)
    if idx >= 0:
        strings = _cstrings(data, idx + len(profile))
        # the first strings are title/author/category/version; the long one is the description
        candidates = [s for s in strings if len(s) < 200]
        long_text = next((s for s in strings if len(s) >= 200), None)
        for key, value in zip(META_ORDER, candidates):
            meta[key] = value
        if long_text:
            meta["description"] = long_text
    assets = sorted({m.group(1).decode("latin-1") for m in ASSET_RE.finditer(data)})
    bundles = sorted({m.group(1).decode("latin-1") for m in BUNDLE_RE.finditer(data)})
    return {
        "format": "FROSTY",
        "magic": "FROSTY",
        "profile": profile if idx >= 0 else None,
        **meta,
        "resources": [{"name": a, "type": "ebx"} for a in assets],
        "actions": [],
        "assets": assets,
        "bundles": bundles,
    }


def parse(path: Path) -> dict:
    data = path.read_bytes()
    record: dict
    if data[:6] == b"FROSTY":
        record = parse_v1(data)
    else:
        try:
            record = parse_v2(data)
        except Exception as exc:  # noqa: BLE001 - report, never crash the inventory
            record = {"format": "unknown", "error": f"{type(exc).__name__}: {exc}",
                      "assets": [], "bundles": [], "resources": [], "actions": []}
    record["file"] = path.name
    record["size"] = len(data)
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("dir", type=Path)
    ls.add_argument("--json", type=Path, default=None)
    sh = sub.add_parser("show")
    sh.add_argument("file", type=Path)
    cf = sub.add_parser("conflicts")
    cf.add_argument("dir", type=Path)
    args = ap.parse_args()

    if args.cmd == "show":
        print(json.dumps(parse(args.file), indent=1))
        return 0

    mods = [parse(p) for p in sorted(args.dir.glob("*.fbmod"))]
    if args.cmd == "list":
        print(f"{len(mods)} mods in {args.dir}\n")
        for m in mods:
            print(f"{m['file']}  [{m['format']}]")
            print(f"    {m.get('title')!r} by {m.get('author')!r} ({m.get('category')}, v{m.get('version')})")
            print(f"    assets {len(m['assets'])}  bundles {len(m['bundles'])}")
        if args.json:
            args.json.write_text(json.dumps(mods, indent=1), encoding="utf-8")
            print(f"\nwrote {args.json}")
        return 0

    # conflicts
    owners: dict[str, list[str]] = {}
    for m in mods:
        for asset in m["assets"]:
            owners.setdefault(asset, []).append(m["file"])
    clashes = {a: f for a, f in owners.items() if len(f) > 1}
    bundle_owners: dict[str, list[str]] = {}
    for m in mods:
        for bundle in m["bundles"]:
            bundle_owners.setdefault(bundle, []).append(m["file"])
    bundle_clashes = {b: f for b, f in bundle_owners.items() if len(f) > 1}

    print(f"{len(mods)} mods, {len(owners)} distinct assets, {len(clashes)} asset conflicts")
    for asset, files in sorted(clashes.items()):
        print(f"  {asset}\n      {', '.join(sorted(set(files)))}")
    print(f"\n{len(bundle_clashes)} bundle conflicts")
    for bundle, files in sorted(bundle_clashes.items()):
        print(f"  {bundle}\n      {', '.join(sorted(set(files)))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
