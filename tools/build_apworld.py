"""Build `mass_effect_andromeda.apworld` — the archive the launcher ships and users drop into
`custom_worlds/`.

Layout inside the zip:
    archipelago.json                      (manifest, read by Archipelago)
    mass_effect_andromeda/__init__.py     (package; zipimport loads it as worlds.<name>)
    mass_effect_andromeda/*.py
    mass_effect_andromeda/datafiles/*.json
    mass_effect_andromeda/docs/*

Usage: python tools/build_apworld.py [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "world" / "mass_effect_andromeda"
DEFAULT_OUT = ROOT / "dist" / "mass_effect_andromeda.apworld"

SKIP_DIRS = {"__pycache__", "test", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    manifest = json.loads((PACKAGE / "archipelago.json").read_text(encoding="utf-8"))
    # The container manifest needs the archiving protocol fields Archipelago validates:
    # compatible_version is the APContainer protocol version (7 for 0.6.x), version is ours.
    container_manifest = {
        "game": manifest["game"],
        "compatible_version": 7,
        "version": manifest.get("world_version", "0.1.0"),
        # Archipelago reads the world's own version from this key (worlds/__init__.py)
        "world_version": manifest.get("world_version", "0.1.0"),
        "minimum_ap_version": manifest.get("minimum_ap_version", "0.6.8"),
        "authors": manifest.get("authors", []),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(PACKAGE)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        files.append(path)

    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("archipelago.json", json.dumps(container_manifest, indent=1))
        for path in files:
            rel = path.relative_to(PACKAGE)
            zf.write(path, f"mass_effect_andromeda/{rel.as_posix()}")

    total = args.out.stat().st_size
    print(f"wrote {args.out} ({total / 1024:.1f} KB, {len(files) + 1} entries)")
    print(f"  game: {manifest['game']}  world_version: {manifest['world_version']}")
    for path in files:
        print(f"  + mass_effect_andromeda/{path.relative_to(PACKAGE).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
