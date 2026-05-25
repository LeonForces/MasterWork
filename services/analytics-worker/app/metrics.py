from __future__ import annotations

from prometheus_client import Counter, Histogram

FRAMES_INPUT = Counter("analytics_frames_input_total", "Input frames per camera", ["camera_id"])
FRAMES_PROCESSED = Counter("analytics_frames_processed_total", "Processed frames per camera", ["camera_id"])
FRAMES_DROPPED = Counter("analytics_frames_dropped_total", "Dropped frames per camera", ["camera_id"])
RECONNECTS = Counter("analytics_rtsp_reconnect_total", "Reconnect attempts per camera", ["camera_id"])
INFERENCE_LATENCY = Histogram("analytics_inference_latency_seconds", "Inference latency", ["camera_id"])
EVENT_LATENCY = Histogram("analytics_object_to_event_latency_seconds", "Object to event latency", ["camera_id"])
EVENTS_CREATED = Counter("analytics_events_created_total", "Events created", ["camera_id", "event_type"])
