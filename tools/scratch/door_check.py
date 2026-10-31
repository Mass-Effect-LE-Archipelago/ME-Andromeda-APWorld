"""Decode tempest_main_LOCK_hallway_door_check: resolve its three imported condition expressions
and print the plot flags each reads, with values in the owner's saves."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import probe_galaxymap_prefab as probe  # noqa: E402
import profsave3 as p  # noqa: E402
from frostbite import vfs  # noqa: E402

WANT = {"833a62d0-c3aa-11e6-96aa-9da18225139c", "6489e150-05a9-11e6-9153-c26d19ee7a9d",
        "024f4d91-0fba-11e5-a9ac-b61ea2435e2d"}
game = vfs.Game()
found = {}
for name in game.iter_names("game/plots/"):
    _d, part = probe.partition_or_none(game, name)
    if part is not None and part.guid.text in WANT:
        found[part.guid.text] = (name, part)
        if len(found) == len(WANT):
            break

D = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
SAVES = ["Chapter33", "0ManualSave", "5AutoSave", "6AutoSave", "Mission", "Chapter34", "Chapter10"]
plots = {s: p.load(D / f"Careerb191e387-{s}").plot for s in SAVES}


def val(plot, g):
    for kind in ("bools", "ints"):
        if g in plot[kind]:
            v = plot[kind][g]
            return {True: "T", False: "f"}.get(v, str(v)) if kind == "bools" else str(v)
    return "."


def walk(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "Guid" and "PlotFlagId" in str(out[-1:] or ""):
                pass
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)


print("saves:", " ".join(SAVES))
for g in WANT:
    if g not in found:
        print(f"{g}: NOT FOUND under game/plots/")
        continue
    name, part = found[g]
    print(f"\n== {name}  ({g})")
    for _inst, obj in part.instance_objects():
        if not isinstance(obj, dict):
            continue
        typ = str(obj.get("$", ""))
        desired = obj.get("DesiredValue")
        flag = ((obj.get("Flag") or {}).get("PlotFlagId") or {}).get("Guid")
        extra = {k: v for k, v in obj.items() if k in ("MatchType", "Name", "Value", "Comparison", "Condition")}
        line = f"  {typ:28s} desired={desired}"
        if flag is not None:
            fg = str(flag)
            line += f" flag={fg}  " + " ".join(val(plots[s], fg) for s in SAVES)
        print(line, extra if extra and flag is None else "")
