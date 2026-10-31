"""Name all 13 save agents by djb2-xor over plausible class names.

Calibrated: djb2_xor('GalaxyDataStateManagerSaveAgent') == 0x066D83C3 (the galaxy agent).
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave"

BASES = [
    "WorldStateManager", "WorldState", "JournalSystem", "Journal", "MEJournal", "JournalData",
    "LootContainer", "Loot", "LootManager", "PartyManager", "Party", "VendorInventory", "Vendor",
    "WorldMap", "WorldMapManager", "EventTracker", "Event", "DestructionManager", "Destruction",
    "CodexListManager", "CodexList", "Codex", "ActivePlayTimer", "PlayTimer", "Notifications",
    "Notification", "Latest", "Customization", "Player", "PlayerSaveGame", "SaveGame", "Inventory",
    "Crafting", "MECrafting", "CraftingProgression", "Research", "Progress", "Progression",
    "StrikeTeam", "Multiplayer", "GalaxyDataStateManager", "Plot", "Space", "Nomad", "Stats",
]
SUFFIXES = ["SaveAgent", "SaveGameAgent", "Agent", "SaveData", "SaveGameData", "Data", "Save"]
PREFIXES = ["", "ME", "Mea"]


def djb2_xor(text: str) -> int:
    h = 5381
    for ch in text.encode("utf-8"):
        h = ((h * 33) ^ ch) & 0xFFFFFFFF
    return h


def main() -> int:
    save = p.load(SAVE)
    wanted = {}
    for agent in save.agents:
        wanted.setdefault(agent.name_hash, agent.index)

    names: dict[int, str] = {}
    for prefix, base, suffix in itertools.product(PREFIXES, BASES, SUFFIXES):
        name = prefix + base + suffix
        h = djb2_xor(name)
        if h in wanted and h not in names:
            names[h] = name

    for h, idx in sorted(wanted.items(), key=lambda kv: kv[1]):
        print(f"  idx {idx:2d}  0x{h:08X}  {names.get(h, '(unresolved)')}")
    print(f"\nresolved {len(names)} of {len(wanted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
