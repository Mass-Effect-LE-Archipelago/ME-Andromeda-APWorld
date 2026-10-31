"""Offline tests for the client core, using real saves and the real check catalogue.

Run from the project root:
    python world/mass_effect_andromeda/test/test_client_core.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "world" / "mass_effect_andromeda"))

import client_core as cc  # noqa: E402

SAVE_DIR = Path.home() / "Documents" / "BioWare" / "Mass Effect Andromeda" / "Save"
EARLY = SAVE_DIR / "Careered8233e3-0ManualSave"   # 87.4% completion
LATE = SAVE_DIR / "Career870ee94-1ManualSave"     # 99.5% completion


def build_detectors() -> list[cc.Detector]:
    checks = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    return [cc.Detector(location_id=i + 1, name=c["name"], guid=c["guid"], kind=c["kind"],
                        region=c["region"]) for i, c in enumerate(checks)]


def test_slot_data_roundtrip() -> None:
    checks = json.loads((ROOT / "data" / "checks.json").read_text(encoding="utf-8"))["checks"]
    slot = {"detectors": [{"id": i + 1, "name": c["name"], "guid": c["guid"], "kind": c["kind"],
                           "region": c["region"]} for i, c in enumerate(checks)]}
    detectors = cc.detectors_from_slot_data(slot)
    assert len(detectors) == len(checks), (len(detectors), len(checks))
    assert all(d.location_id > 0 and d.guid for d in detectors)
    print(f"slot data: {len(detectors)} detectors rebuilt")


def test_tracker() -> None:
    detectors = build_detectors()
    tracker = cc.CheckTracker(detectors)
    early = cc.CareerState.read(EARLY)
    late = cc.CareerState.read(LATE)

    first = tracker.poll(early)
    print(f"bind on the 87% save: {len(first)} checks already satisfied")
    assert len(first) <= len(detectors)

    second = tracker.poll(early)
    assert second == [], "polling the same state twice must not re-report checks"

    new = tracker.poll(late)
    print(f"moving to the 99.5% save: {len(new)} new checks")
    assert new, "expected new checks between two different playthroughs"

    ids = [d.location_id for d in new]
    assert len(ids) == len(set(ids)), "a location must not be reported twice"
    again = tracker.poll(late)
    assert again == [], "the same later state must not re-report"
    sample = ", ".join(d.name for d in new[:3])
    print(f"  e.g. {sample}")


def test_delivery_queue() -> None:
    # A pre-existing directory: the sandbox here permits writes into existing directories but
    # not into ones a subprocess creates at runtime.
    scratch = ROOT / "tools" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "client-core-pending-test.json"
    if path.exists():
        path.unlink()
    queue = cc.DeliveryQueue(path)
    queue.add(1, "Eos Access", 1)
    queue.add(2, "Carnifex pistols", 1)
    assert len(queue.unapplied) == 2
    queue.mark_applied(queue.items[0], "logged only")
    reloaded = cc.DeliveryQueue(path)
    assert len(reloaded.items) == 2
    assert len(reloaded.unapplied) == 1
    assert reloaded.items[0].applied is True
    print("delivery queue: persisted and reloaded correctly")


def test_effects_lookup() -> None:
    assert cc.effect_for("Eos Access", {}) is None
    effects = {"Eos Access": {"kind": "unlock", "target": "eos"}}
    assert cc.effect_for("Eos Access", effects) == {"kind": "unlock", "target": "eos"}
    print("effect lookup: ok")


if __name__ == "__main__":
    test_slot_data_roundtrip()
    test_tracker()
    test_delivery_queue()
    test_effects_lookup()
    print("\nALL CLIENT CORE TESTS PASSED")
