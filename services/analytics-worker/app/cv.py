from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import cv2
import numpy as np

try:
    import av  # type: ignore
except Exception:  # pragma: no cover
    av = None

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort  # type: ignore
except Exception:  # pragma: no cover
    DeepSort = None

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None


@dataclass
class Detection:
    bbox: list[float]  # [x1, y1, x2, y2]
    confidence: float
    class_name: str


class FrameSource:
    def __init__(self, source_url: str) -> None:
        self.source_url = source_url

    def iter_frames(self) -> Iterator[np.ndarray]:
        if av is not None:
            try:
                options = {"rtsp_transport": "tcp", "fflags": "nobuffer"}
                container = av.open(self.source_url, options=options)
                stream = container.streams.video[0]
                for frame in container.decode(stream):
                    yield frame.to_ndarray(format="bgr24")
                return
            except Exception:
                pass

        cap = cv2.VideoCapture(self.source_url)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open source: {self.source_url}")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
        cap.release()


class Detector:
    def __init__(
        self,
        model_name: str,
        allowed_classes: set[str],
        confidence_threshold: float = 0.25,
        use_mock: bool = False,
    ) -> None:
        self.allowed_classes = {class_name.lower() for class_name in allowed_classes}
        self.confidence_threshold = confidence_threshold
        self.use_mock = use_mock or YOLO is None
        self.model = None
        if not self.use_mock:
            self.model = YOLO(model_name)

    def detect(self, frame: np.ndarray) -> tuple[list[Detection], float]:
        start = perf_counter()
        if self.use_mock:
            h, w = frame.shape[:2]
            mock = Detection(bbox=[w * 0.35, h * 0.35, w * 0.65, h * 0.75], confidence=0.65, class_name="person")
            latency = perf_counter() - start
            return [mock], latency

        assert self.model is not None
        results = self.model.predict(frame, conf=self.confidence_threshold, verbose=False)
        detections: list[Detection] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                cls_idx = int(box.cls[0].item())
                class_name = names[cls_idx]
                conf = float(box.conf[0].item())
                if self.allowed_classes and class_name.lower() not in self.allowed_classes:
                    continue
                xyxy = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        bbox=[float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                        confidence=conf,
                        class_name=class_name,
                    )
                )
        latency = perf_counter() - start
        return detections, latency


class TrackerAdapter:
    def __init__(self) -> None:
        self.fallback_counter = 0
        self.fallback_tracks: dict[str, dict[str, Any]] = {}
        self.fallback_frame_idx = 0
        self.fallback_match_iou = 0.3
        self.fallback_max_idle_frames = 30
        self.tracker = None
        if DeepSort is not None:
            self.tracker = DeepSort(max_age=30, embedder="mobilenet")

    @staticmethod
    def _iou(box_a: list[float], box_b: list[float]) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - inter
        if union <= 0:
            return 0.0
        return inter / union

    def _update_fallback(self, detections: list[Detection]) -> list[dict[str, Any]]:
        self.fallback_frame_idx += 1
        stale_ids = [
            track_id
            for track_id, state in self.fallback_tracks.items()
            if self.fallback_frame_idx - int(state["last_seen_frame"]) > self.fallback_max_idle_frames
        ]
        for track_id in stale_ids:
            del self.fallback_tracks[track_id]

        output: list[dict[str, Any]] = []
        used_tracks: set[str] = set()
        for det in detections:
            best_track_id: str | None = None
            best_iou = 0.0
            for track_id, state in self.fallback_tracks.items():
                if track_id in used_tracks:
                    continue
                if state["object_class"] != det.class_name:
                    continue
                iou = self._iou(state["bbox"], det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is None or best_iou < self.fallback_match_iou:
                self.fallback_counter += 1
                best_track_id = str(self.fallback_counter)

            self.fallback_tracks[best_track_id] = {
                "bbox": det.bbox,
                "object_class": det.class_name,
                "last_seen_frame": self.fallback_frame_idx,
            }
            used_tracks.add(best_track_id)
            output.append(
                {
                    "track_id": best_track_id,
                    "bbox": det.bbox,
                    "confidence": det.confidence,
                    "object_class": det.class_name,
                }
            )
        return output

    def update(self, detections: list[Detection], frame: np.ndarray) -> list[dict[str, Any]]:
        if self.tracker is None:
            return self._update_fallback(detections)

        ds_input = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            ds_input.append(([x1, y1, x2 - x1, y2 - y1], det.confidence, det.class_name))

        tracks = self.tracker.update_tracks(ds_input, frame=frame)
        output: list[dict[str, Any]] = []
        for trk in tracks:
            if not trk.is_confirmed():
                continue
            ltrb = trk.to_ltrb()
            output.append(
                {
                    "track_id": str(trk.track_id),
                    "bbox": [float(ltrb[0]), float(ltrb[1]), float(ltrb[2]), float(ltrb[3])],
                    "confidence": 1.0,
                    "object_class": trk.det_class or "unknown",
                }
            )
        return output
