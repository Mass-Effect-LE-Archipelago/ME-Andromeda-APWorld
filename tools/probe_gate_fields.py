"""Map where the `alwaysfalse` condition import sits inside each planet destination.

Finds every field path whose value references the GUID, so the blocking field can be told apart
from fields where "false" is legitimate.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from frostbite.partition import Partition  # noqa: E402
from frostbite.dbobject import Guid  # noqa: E402

FALSE_GUID = "c6660dbe-3614-11e5-aa63-b2e3b7222cc5"
TRUE_GUID = "bf899768-3614-11e5-aa63-b2e3b7222cc5"
PLANETS = [
    "eos", "voeld", "havarl", "kadarahub", "kadaraunc", "elaaden", "eladen", "h047c",
    "meridianhub", "kearnosii", "ayahub", "nexushub",
]
CACHE = ROOT / "tools" / "scratch" / "dests"
CACHE.mkdir(parents=True, exist_ok=True)


def walk(value, path: str, hits: list[tuple[str, str]]) -> None:
    if isinstance(value, Guid):
        text = str(value).lower()
        if FALSE_GUID in text or TRUE_GUID in text:
            hits.append((path, "false" if FALSE_GUID in text else "true"))
        return
    if isinstance(value, str):
        low = value.lower()
        if FALSE_GUID in low or TRUE_GUID in low:
            hits.append((path, "false" if FALSE_GUID in low else "true"))
        return
    if isinstance(value, dict):
        for key, child in value.items():
            walk(child, f"{path}.{key}" if path else str(key), hits)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            walk(child, f"{path}[{index}]", hits)


def main() -> int:
    import subprocess
    names = [line.strip() for line in
             (ROOT / "data" / "asset-names.txt").read_text(encoding="utf-8").splitlines()]
    targets = []
    for planet in PLANETS:
        matches = [n for n in names
                   if n.startswith("game/space/destinations/") and planet in n.lower()
                   and n.endswith(f"destination_{'plt_' if planet not in ('nexushub',) else 'stn_'}{planet}")]
        targets.extend(matches[:1])

    print(f"destinations to inspect: {len(targets)}")
    for name in targets:
        out = CACHE / (name.rsplit("/", 1)[-1] + ".bin")
        if not out.exists():
            result = subprocess.run([sys.executable, str(ROOT / "tools" / "frostbite" / "run.py"),
                                     "dump", name, "--out", str(out)],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  SKIP {name}: {result.stderr.strip()[:60]}")
                continue
        try:
            part = Partition(out.read_bytes())
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIP {name}: {exc}")
            continue
        hits: list[tuple[str, str]] = []
        for _obj_name, obj in part.instance_objects():
            walk(obj, "", hits)
        label = name.rsplit("/", 1)[-1]
        print(f"\n{label}")
        if not hits:
            print("   (no alwaysfalse/alwaystrue reference)")
        for path, kind in hits:
            print(f"   {kind:5s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
