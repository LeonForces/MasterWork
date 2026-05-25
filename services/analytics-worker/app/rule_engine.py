from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            else:
                xints = p1x
            if p1x == p2x or x <= xints:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> int:
    val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else 2


def segments_intersect(
    p1: tuple[float, float],
    q1: tuple[float, float],
    p2: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    return o1 != o2 and o3 != o4


@dataclass
class TrackState:
    last_point: tuple[float, float] | None = None
    zone_entered_at: dict[str, datetime] = field(default_factory=dict)
    fired_keys: set[str] = field(default_factory=set)


class RuleEngine:
    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self.track_states: dict[str, TrackState] = {}

    def evaluate(
        self,
        tracks: list[dict[str, Any]],
        rules: list[dict[str, Any]],
        zones: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        zone_by_id = {z["zone_id"]: z for z in zones}
        generated: list[dict[str, Any]] = []

        for track in tracks:
            track_id = str(track["track_id"])
            st = self.track_states.setdefault(track_id, TrackState())
            current_point = bbox_center(track["bbox"])
            ts = now_utc()

            for rule in rules:
                rule_type = rule["rule_type"]
                params = rule.get("params") or {}
                zone_id = params.get("zone_id")
                zone = zone_by_id.get(zone_id) if zone_id else None

                if rule_type == "zone_enter" and zone:
                    polygon = (zone.get("geometry") or {}).get("points", [])
                    inside_now = point_in_polygon(current_point, polygon)
                    inside_prev = point_in_polygon(st.last_point, polygon) if st.last_point else False
                    if inside_now and not inside_prev:
                        dedup = f"{self.camera_id}:{rule['rule_id']}:{track_id}"
                        generated.append(
                            self._build_event(
                                track=track,
                                rule=rule,
                                event_type="zone_enter",
                                dedup_key=dedup,
                                zone_id=zone_id,
                            )
                        )

                if rule_type == "line_cross":
                    line_points = (params.get("line") or [])
                    if len(line_points) == 2 and st.last_point is not None:
                        p1 = (float(line_points[0][0]), float(line_points[0][1]))
                        p2 = (float(line_points[1][0]), float(line_points[1][1]))
                        line_key = f"line_cross:{rule['rule_id']}:{track_id}"
                        if segments_intersect(st.last_point, current_point, p1, p2) and line_key not in st.fired_keys:
                            st.fired_keys.add(line_key)
                            dedup = f"{self.camera_id}:{rule['rule_id']}:{track_id}:line_cross"
                            generated.append(
                                self._build_event(
                                    track=track,
                                    rule=rule,
                                    event_type="line_cross",
                                    dedup_key=dedup,
                                    zone_id=zone_id,
                                )
                            )

                if rule_type == "dwell_time" and zone:
                    threshold = int(params.get("seconds", 5))
                    polygon = (zone.get("geometry") or {}).get("points", [])
                    inside = point_in_polygon(current_point, polygon)
                    if inside:
                        start_ts = st.zone_entered_at.setdefault(zone_id, ts)
                        dwell_key = f"{rule['rule_id']}:{zone_id}:{track_id}:{threshold}"
                        if (ts - start_ts).total_seconds() >= threshold and dwell_key not in st.fired_keys:
                            st.fired_keys.add(dwell_key)
                            dedup = f"{self.camera_id}:{rule['rule_id']}:{track_id}:dwell:{threshold}"
                            generated.append(
                                self._build_event(
                                    track=track,
                                    rule=rule,
                                    event_type="dwell_time",
                                    dedup_key=dedup,
                                    zone_id=zone_id,
                                )
                            )
                    else:
                        st.zone_entered_at.pop(zone_id, None)

            st.last_point = current_point
        return generated

    @staticmethod
    def _build_event(
        track: dict[str, Any],
        rule: dict[str, Any],
        event_type: str,
        dedup_key: str,
        zone_id: str | None,
    ) -> dict[str, Any]:
        return {
            "track_id": str(track["track_id"]),
            "rule_id": rule["rule_id"],
            "event_type": event_type,
            "severity": rule.get("severity", "medium"),
            "occurred_at": now_utc(),
            "confidence": float(track.get("confidence", 0.5)),
            "snapshot_path": None,
            "dedup_key": dedup_key,
            "object_class": track.get("object_class", "unknown"),
            "zone_id": zone_id,
            "attributes": {
                "object_class": track.get("object_class", "unknown"),
                "bbox": track.get("bbox"),
                "track_confidence": float(track.get("confidence", 0.0)),
            },
        }
