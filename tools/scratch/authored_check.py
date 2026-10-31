import json, sys
from pathlib import Path
sys.path.insert(0, "tools"); sys.path.insert(0, "tools/frostbite")
import fbmod, modmanager
edited = Path("tools/scratch/edited-title.fbmod")
record = fbmod.parse(edited)
print("inventory parses the authored mod:", record["title"], "| assets", len(record["assets"]),
      "| format", record["format"])
work = Path("tools/scratch/authored")
(work / "mods").mkdir(parents=True, exist_ok=True)
(work / "mods" / "authored.fbmod").write_bytes(edited.read_bytes())
profile = work / "profile.json"
profile.write_text(json.dumps({"mods": [{"file": "authored.fbmod", "enabled": True, "order": 10,
                                         "title": record["title"]}]}), encoding="utf-8")
modmanager.cmd_deploy(work / "mods", profile, work / "deployed")
modmanager.cmd_verify(work / "deployed")
modmanager.cmd_restore(work / "deployed")
print("files left:", len(list((work / "deployed").glob("*"))))
