from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("analytics_cv", ROOT / "app" / "cv.py")
assert spec is not None and spec.loader is not None
cv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cv
spec.loader.exec_module(cv)


def _det(bbox: list[float], class_name: str = "person") -> cv.Detection:
    return cv.Detection(bbox=bbox, confidence=0.9, class_name=class_name)


def test_fallback_tracker_keeps_track_id_for_small_motion() -> None:
    adapter = cv.TrackerAdapter()
    adapter.tracker = None
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    tracks_1 = adapter.update([_det([100, 100, 150, 180])], frame)
    tracks_2 = adapter.update([_det([104, 102, 154, 182])], frame)

    assert len(tracks_1) == 1
    assert len(tracks_2) == 1
    assert tracks_1[0]["track_id"] == tracks_2[0]["track_id"]


def test_fallback_tracker_creates_new_id_for_far_object() -> None:
    adapter = cv.TrackerAdapter()
    adapter.tracker = None
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    tracks_1 = adapter.update([_det([20, 20, 60, 80])], frame)
    tracks_2 = adapter.update([_det([420, 320, 470, 390])], frame)

    assert tracks_1[0]["track_id"] != tracks_2[0]["track_id"]
