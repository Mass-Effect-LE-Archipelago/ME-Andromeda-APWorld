"""Identify agent hashes by computing DJB2-XOR over known agent class names."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import profsave3 as p  # noqa: E402

SAVE = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save" / "Career870ee94-1ManualSave"

CANDIDATES = [
    "ActivePlayTimerAgent", "CodexListManagerAgent", "DestructionManagerAgent", "EventTrackerAgent",
    "GalaxyDataManagerAgent", "JournalSystemAgent", "LatestAgent", "LootContainerAgent",
    "NotificationsAgent", "PartyManagerAgent", "PlotAgent", "VendorInventoryAgent", "WorldMapAgent",
    "WorldStateManagerAgent", "CustomizationAgent", "PlayerSaveGameAgent", "MECraftingAgent",
    "CraftingAgent", "InventoryAgent", "PlayerAgent", "StrikeTeamAgent", "MultiplayerAgent",
]
SUFFIXES = ["", "SaveAgent", "SaveGameAgent", "AgentData", "SaveData"]


def djb2_xor(text: str) -> int:
    h = 5381
    for ch in text.encode("utf-8"):
        h = ((h * 33) ^ ch) & 0xFFFFFFFF
    return h


def main() -> int:
    save = p.load(SAVE)
    hashes = {}
    for agent in save.agents:
        hashes.setdefault(agent.name_hash, []).append(agent.index)

    print(f"agent hashes in {SAVE.name}: {len(hashes)}")
    for h, idx in sorted(hashes.items(), key=lambda kv: kv[1][0]):
        print(f"  0x{h:08X}  idx {idx}")

    print("\nmatching candidate class names:")
    found = 0
    for base in CANDIDATES:
        for suffix in SUFFIXES:
            name = base if suffix == "" or base.endswith(suffix) else base + suffix
            h = djb2_xor(name)
            if h in hashes:
                print(f"  0x{h:08X}  {name:36s} -> idx {hashes[h]}")
                found += 1
                break
    print(f"matched {found} of {len(hashes)} hashes")

    unresolved = [h for h in hashes if not any(djb2_xor(b) == h or djb2_xor(b + 'SaveAgent') == h for b in CANDIDATES)]
    print(f"unresolved: {[f'0x{h:08X}' for h in unresolved]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
