"""List every plot flag GUID an asset references (with the instance type and field), plus its value
in the owner's exploration saves. Usage: python asset_flags.py <asset name> [...]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import probe_galaxymap_prefab as probe  # noqa: E402
import profsave3 as p  # noqa: E402
from frostbite import vfs  # noqa: E402

J = json.loads((ROOT / "docs" / "plot-flag-join.json").read_text(encoding="utf-8"))
names = J["guid_to_names"]
D = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
SAVES = ["0ManualSave", "5AutoSave", "6AutoSave", "Mission", "Chapter34", "Chapter10"]
plots = {s: p.load(D / f"Careerb191e387-{s}").plot for s in SAVES}


def val(plot, g):
    for kind in ("bools", "ints"):
        if g in plot[kind]:
            v = plot[kind][g]
            return {True: "T", False: "f"}.get(v, str(v)) if kind == "bools" else str(v)
    return "."


def flags(o, path, out):
    if isinstance(o, dict):
        if "PlotFlagId" in o and isinstance(o["PlotFlagId"], dict) and "Guid" in o["PlotFlagId"]:
            out.append((path, str(o["PlotFlagId"]["Guid"])))
        for k, v in o.items():
            if k != "PlotFlagId":
                flags(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            flags(v, f"{path}[{i}]", out)


game = vfs.Game()
print("saves:", " ".join(SAVES))
for name in sys.argv[1:]:
    _d, part = probe.partition_or_none(game, name)
    print(f"\n== {name}")
    if part is None:
        print("  unreadable")
        continue
    for _inst, obj in part.instance_objects():
        if not isinstance(obj, dict):
            continue
        out = []
        flags(obj, "", out)
        typ = str(obj.get("$", "")).replace("base:", "")
        for path, g in out:
            n = names.get(g)
            n = (n[0] if isinstance(n, list) else n) or ""
            extra = {k: obj[k] for k in ("DesiredValue", "CheckOnStart", "Value", "SetValue") if k in obj}
            print(f"  {typ[:34]:34s} {path[:40]:40s} {g}  " + " ".join(f"{val(plots[s], g):>3s}" for s in SAVES)
                  + f"  {extra} {n.split('/')[-1][:50]}")
