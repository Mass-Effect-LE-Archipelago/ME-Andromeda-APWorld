"""Client core: turn save files into Archipelago location checks, and queue items back.

No Archipelago imports here on purpose — this is the part that can be tested offline against
real saves (see `test_client_core.py`). `client.py` is the thin AP wrapper around it.

Detection rules (documented because they are heuristics):
  * bool detector  -> the flag is true
  * int detector   -> the value differs from the value captured when the career was bound
  * float detector -> ignored (no stable semantics)
The bind baseline is the first save the client sees for a career; satisfied detectors at bind
are still reported, because a fresh career legitimately has a few flags already set and an
already-checked location is harmless to send twice.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # inside a checkout the parser lives in tools/; a shipped .apworld carries its own copy
    import profsave3 as p
except ImportError:  # pragma: no cover - exercised by the packaged client
    from . import profsave as p

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"


@dataclass(frozen=True)
class Detector:
    location_id: int
    name: str
    guid: str
    kind: str
    region: str

    @classmethod
    def from_slot_data(cls, entry: dict[str, Any]) -> "Detector":
        return cls(location_id=int(entry["id"]), name=str(entry["name"]), guid=str(entry["guid"]),
                   kind=str(entry["kind"]), region=str(entry.get("region", "")))


def detectors_from_slot_data(slot_data: dict[str, Any]) -> list[Detector]:
    raw = slot_data.get("detectors") or []
    return [Detector.from_slot_data(entry) for entry in raw]


@dataclass
class CareerState:
    save_path: Path
    save_name: str
    timestamp: str
    bools: dict[str, bool]
    ints: dict[str, int]
    floats: dict[str, float]
    mtime: float
    size: int
    world_map: list[str] = field(default_factory=list)
    level: str = ""

    @classmethod
    def read(cls, path: Path) -> "CareerState":
        save = p.load(path)
        plot = save.plot
        stat = path.stat()
        return cls(save_path=path, save_name=save.data.get("save_file_name", path.name),
                   timestamp=save.data.get("timestamp_iso", ""),
                   bools=dict(plot.get("bools", {})), ints=dict(plot.get("ints", {})),
                   floats=dict(plot.get("floats", {})), mtime=stat.st_mtime, size=stat.st_size,
                   world_map=list(getattr(save, "world_map", []) or []),
                   # entry1 is the save's location tag (e.g. SavedGame_HUB_Meridian); data's
                   # level_name is the engine root level and is the same in every save
                   level=save.header.get("entry1", ""))


def latest_save(directory: Path = SAVE_DIR) -> Path | None:
    """Newest save file in the save folder (the game writes 'Career<id>-<n><Type>' names)."""
    if not directory.exists():
        return None
    candidates = [f for f in directory.iterdir() if f.is_file() and f.name.startswith("Career")]
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_mtime)


class CheckTracker:
    """Maps save state to newly satisfied locations, reporting each once."""

    def __init__(self, detectors: list[Detector]) -> None:
        self.detectors = [d for d in detectors if d.kind in ("bools", "ints")]
        self.baseline_ints: dict[str, int] = {}
        self.reported: set[int] = set()
        self.bound = False

    def bind(self, state: CareerState) -> None:
        self.baseline_ints = dict(state.ints)
        self.bound = True

    def satisfied(self, state: CareerState) -> list[Detector]:
        out: list[Detector] = []
        for det in self.detectors:
            if det.kind == "bools":
                if state.bools.get(det.guid, False):
                    out.append(det)
            else:
                value = state.ints.get(det.guid)
                if value is None:
                    continue
                base = self.baseline_ints.get(det.guid)
                if base is None:
                    # int flag that did not exist at bind time: appearing at all is progress
                    out.append(det)
                elif value != base:
                    out.append(det)
        return out

    def poll(self, state: CareerState) -> list[Detector]:
        if not self.bound:
            self.bind(state)
        new = [d for d in self.satisfied(state) if d.location_id not in self.reported]
        self.reported.update(d.location_id for d in new)
        return new


class WorldMapTracker:
    """Reports galaxy-map locations that appear after the career was bound.

    Keys are runtime ids (see docs/WORLDMAP-AGENT.md). They only ever appear, so a bind-time
    baseline plus "not seen before" is enough — no semantics needed to use them as progress.
    """

    def __init__(self, labels: dict[str, dict] | None = None) -> None:
        self.seen: set[str] = set()
        self.bound = False
        self.labels = labels or {}

    def bind(self, state: CareerState) -> None:
        self.seen = set(state.world_map)
        self.bound = True

    def poll(self, state: CareerState) -> list[str]:
        if not self.bound:
            self.bind(state)
        # the agent stores the same location in two mirrors lists, so de-duplicate per poll
        new = list(dict.fromkeys(key for key in state.world_map if key not in self.seen))
        self.seen.update(new)
        return new

    def label(self, key: str) -> str:
        record = self.labels.get(key)
        return f"{key} (first seen at {record['step']})" if record else key


@dataclass
class PendingItem:
    item_id: int
    name: str
    player: int
    received_at: float = field(default_factory=time.time)
    applied: bool = False
    note: str = ""


class DeliveryQueue:
    """Items that arrived from the multiworld, persisted so a restart does not lose them."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: list[PendingItem] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.items = [PendingItem(**entry) for entry in raw.get("items", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"items": [item.__dict__ for item in self.items]}, indent=1),
                             encoding="utf-8")

    def add(self, item_id: int, name: str, player: int) -> PendingItem:
        item = PendingItem(item_id=item_id, name=name, player=player)
        self.items.append(item)
        self.save()
        return item

    @property
    def unapplied(self) -> list[PendingItem]:
        return [item for item in self.items if not item.applied]

    def mark_applied(self, item: PendingItem, note: str) -> None:
        item.applied = True
        item.note = note
        self.save()


def effect_for(item_name: str, effects: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Item name -> delivery effect, from the world's slot data once the flags are known."""
    return effects.get(item_name)
