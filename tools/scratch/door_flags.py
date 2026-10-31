"""Values of the flags referenced by the M7 / Tempest-door plot assets across the exploration saves."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profsave3 as p  # noqa: E402

D = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
J = json.loads((Path(__file__).resolve().parents[2] / "docs" / "plot-flag-join.json").read_text(encoding="utf-8"))
KEYS = ["mea_m7_meridian_mission_available", "crit_tempest_07", "hub_meridian_docking_available",
        "tempest_main_lock_hallway_door_check", "galaxymap_unlock_meridian"]
SAVES = ["Chapter33", "0ManualSave", "5AutoSave", "6AutoSave", "Mission", "Chapter34", "Chapter10"]
loaded = {s: p.load(D / f"Careerb191e387-{s}").plot for s in SAVES}


def val(plot, g):
    for kind in ("bools", "ints", "floats"):
        if g in plot[kind]:
            v = plot[kind][g]
            return {True: "T", False: "f"}.get(v, str(v)) if kind == "bools" else str(v)
    return "."


print(f"{'asset':52s} {'guid':8s} {'kind':28s} " + " ".join(f"{s[-7:]:>7s}" for s in SAVES))
for a in J["assets"]:
    if any(k in a["name"] for k in KEYS):
        for f in a["flags"]:
            row = " ".join(f"{val(loaded[s], f['guid']):>7s}" for s in SAVES)
            print(f"{a['name'].split('/')[-1][:52]:52s} {f['guid'][:8]} {f['path'].split('.')[0][:28]:28s} {row}")
