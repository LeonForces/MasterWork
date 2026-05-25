from __future__ import annotations

import logging
import queue
import threading
import time
from time import perf_counter
from typing import Any

import numpy as np
from prometheus_client import start_http_server

from app.cv import Detector, FrameSource, TrackerAdapter
from app.db import get_camera_rules_and_zones, list_active_cameras, persist_events, upsert_track
from app.metrics import (
    EVENTS_CREATED,
    EVENT_LATENCY,
    FRAMES_DROPPED,
    FRAMES_INPUT,
    FRAMES_PROCESSED,
    INFERENCE_LATENCY,
    RECONNECTS,
)
from app.rule_engine import RuleEngine
from app.settings import settings

logger = logging.getLogger("analytics-worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class LatestFrameQueue:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=1)

    def put(self, frame: np.ndarray) -> None:
        if self._queue.full():
            try:
                self._queue.get_nowait()
                FRAMES_DROPPED.labels(camera_id=self.camera_id).inc()
            except queue.Empty:
                pass
        self._queue.put_nowait(frame)

    def get(self, timeout: float = 1.0) -> np.ndarray:
        return self._queue.get(timeout=timeout)


class CameraPipeline:
    def __init__(self, camera: dict[str, Any]):
        self.camera = camera
        self.camera_id = camera["camera_id"]
        self.source_url = camera["rtsp_url"]
        self.frame_delay_seconds = 1.0 / max(float(camera.get("fps_target") or 1), 1.0)
        self.stop_event = threading.Event()
        self.frame_queue = LatestFrameQueue(self.camera_id)
        self.detector = Detector(
            model_name=settings.detector_model,
            allowed_classes=settings.allowed_classes,
            confidence_threshold=settings.detector_confidence,
            use_mock=settings.use_mock_detector,
        )
        self.tracker = TrackerAdapter()
        self.rule_engine = RuleEngine(self.camera_id)
        self.rules: list[dict[str, Any]] = []
        self.zones: list[dict[str, Any]] = []
        self.last_rules_refresh = 0.0

        self.capture_thread = threading.Thread(target=self._capture_loop, name=f"capture-{self.camera_id}", daemon=True)
        self.process_thread = threading.Thread(target=self._process_loop, name=f"process-{self.camera_id}", daemon=True)

    def start(self) -> None:
        self.capture_thread.start()
        self.process_thread.start()
        logger.info("Started camera pipeline %s", self.camera_id)

    def stop(self) -> None:
        self.stop_event.set()
        self.capture_thread.join(timeout=5)
        self.process_thread.join(timeout=5)
        logger.info("Stopped camera pipeline %s", self.camera_id)

    def _refresh_rules(self) -> None:
        now = time.time()
        if now - self.last_rules_refresh < settings.rules_refresh_seconds:
            return
        self.rules, self.zones = get_camera_rules_and_zones(self.camera_id)
        self.last_rules_refresh = now

    def _capture_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                source = FrameSource(self.source_url)
                for frame in source.iter_frames():
                    if self.stop_event.is_set():
                        break
                    FRAMES_INPUT.labels(camera_id=self.camera_id).inc()
                    self.frame_queue.put(frame)
                    time.sleep(self.frame_delay_seconds)
                logger.warning("Source stream ended for camera %s, reconnecting", self.camera_id)
            except Exception as exc:
                logger.exception("Capture error for camera %s: %s", self.camera_id, exc)

            RECONNECTS.labels(camera_id=self.camera_id).inc()
            time.sleep(settings.reconnect_backoff_seconds)

    def _process_loop(self) -> None:
        while not self.stop_event.is_set():
            self._refresh_rules()
            try:
                frame = self.frame_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            process_start = perf_counter()
            detections, inference_latency = self.detector.detect(frame)
            INFERENCE_LATENCY.labels(camera_id=self.camera_id).observe(inference_latency)

            tracks = self.tracker.update(detections, frame)
            for track in tracks:
                upsert_track(self.camera_id, track)

            generated_events = self.rule_engine.evaluate(tracks, self.rules, self.zones)
            inserted = persist_events(self.camera_id, generated_events)
            process_latency = perf_counter() - process_start

            for event in generated_events:
                EVENTS_CREATED.labels(camera_id=self.camera_id, event_type=event["event_type"]).inc()
            for _ in range(inserted):
                EVENT_LATENCY.labels(camera_id=self.camera_id).observe(process_latency)

            FRAMES_PROCESSED.labels(camera_id=self.camera_id).inc()


class CameraManager:
    def __init__(self) -> None:
        self.pipelines: dict[str, CameraPipeline] = {}
        self.lock = threading.Lock()

    def reconcile(self, cameras: list[dict[str, Any]]) -> None:
        active_ids = {camera["camera_id"] for camera in cameras}
        with self.lock:
            for camera in cameras:
                camera_id = camera["camera_id"]
                if camera_id not in self.pipelines:
                    pipeline = CameraPipeline(camera)
                    self.pipelines[camera_id] = pipeline
                    pipeline.start()

            for camera_id in list(self.pipelines.keys()):
                if camera_id not in active_ids:
                    self.pipelines[camera_id].stop()
                    del self.pipelines[camera_id]

    def stop_all(self) -> None:
        with self.lock:
            for pipeline in self.pipelines.values():
                pipeline.stop()
            self.pipelines.clear()


def main() -> None:
    start_http_server(settings.metrics_port)
    logger.info("Analytics metrics server started on :%s", settings.metrics_port)

    manager = CameraManager()
    try:
        while True:
            camera_rows = list_active_cameras()
            manager.reconcile(camera_rows)
            time.sleep(settings.camera_refresh_seconds)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
