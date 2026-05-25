from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("analytics_rule_engine", ROOT / "app" / "rule_engine.py")
assert spec is not None and spec.loader is not None
re = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = re
spec.loader.exec_module(re)


def _track(track_id: str, bbox: list[float], obj_class: str = "person") -> dict:
    return {
        "track_id": track_id,
        "bbox": bbox,
        "confidence": 0.9,
        "object_class": obj_class,
    }


def test_zone_enter_once() -> None:
    engine = re.RuleEngine(camera_id="cam-1")
    rules = [{"rule_id": "r-zone", "rule_type": "zone_enter", "severity": "high", "params": {"zone_id": "z1"}}]
    zones = [{"zone_id": "z1", "geometry": {"points": [[0, 0], [10, 0], [10, 10], [0, 10]]}}]

    # Outside
    ev1 = engine.evaluate([_track("t1", [20, 20, 22, 22])], rules, zones)
    # Entering
    ev2 = engine.evaluate([_track("t1", [2, 2, 4, 4])], rules, zones)
    # Staying inside should not trigger another enter
    ev3 = engine.evaluate([_track("t1", [3, 3, 5, 5])], rules, zones)

    assert ev1 == []
    assert len(ev2) == 1
    assert ev2[0]["event_type"] == "zone_enter"
    assert ev3 == []


def test_line_cross_detected() -> None:
    engine = re.RuleEngine(camera_id="cam-1")
    rules = [
        {
            "rule_id": "r-line",
            "rule_type": "line_cross",
            "severity": "high",
            "params": {"line": [[5, 0], [5, 10]]},
        }
    ]
    zones: list[dict] = []

    # Move from left to right through x=5 line.
    ev1 = engine.evaluate([_track("t1", [1, 4, 2, 5])], rules, zones)
    ev2 = engine.evaluate([_track("t1", [8, 4, 9, 5])], rules, zones)
    # Move back through line. For the same track and rule the event must stay deduplicated.
    ev3 = engine.evaluate([_track("t1", [1, 4, 2, 5])], rules, zones)

    assert ev1 == []
    assert len(ev2) == 1
    assert ev2[0]["event_type"] == "line_cross"
    assert ev3 == []


def test_dwell_time_threshold(monkeypatch) -> None:
    engine = re.RuleEngine(camera_id="cam-1")
    rules = [{"rule_id": "r-dwell", "rule_type": "dwell_time", "severity": "high", "params": {"zone_id": "z1", "seconds": 5}}]
    zones = [{"zone_id": "z1", "geometry": {"points": [[0, 0], [10, 0], [10, 10], [0, 10]]}}]

    timeline = [
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 6, tzinfo=timezone.utc),
    ]

    idx = {"i": 0}

    def fake_now() -> datetime:
        return timeline[idx["i"]]

    monkeypatch.setattr(re, "now_utc", fake_now)

    # Enter zone at t=0
    ev1 = engine.evaluate([_track("t1", [2, 2, 4, 4])], rules, zones)
    idx["i"] = 1
    # Still below threshold
    ev2 = engine.evaluate([_track("t1", [2, 2, 4, 4])], rules, zones)
    idx["i"] = 2
    # Above threshold, should fire once
    ev3 = engine.evaluate([_track("t1", [2, 2, 4, 4])], rules, zones)

    assert ev1 == []
    assert ev2 == []
    assert len(ev3) == 1
    assert ev3[0]["event_type"] == "dwell_time"
