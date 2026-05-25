from __future__ import annotations

from typing import Any


SUPPORTED_ZONE_TYPES = {"polygon", "line"}
SUPPORTED_RULE_TYPES = {"zone_enter", "line_cross", "dwell_time"}


def _is_point(point: Any) -> bool:
    if not isinstance(point, list) or len(point) != 2:
        return False
    return all(isinstance(value, (int, float)) for value in point)


def validate_geometry(zone_type: str, geometry: dict[str, Any]) -> str | None:
    if zone_type not in SUPPORTED_ZONE_TYPES:
        return f"Unsupported zone_type '{zone_type}'"
    if not isinstance(geometry, dict):
        return "geometry must be an object"

    points = geometry.get("points")
    if not isinstance(points, list):
        return "geometry.points must be a list"
    if zone_type == "polygon" and len(points) < 3:
        return "polygon requires at least 3 points"
    if zone_type == "line" and len(points) != 2:
        return "line requires exactly 2 points"
    if any(not _is_point(point) for point in points):
        return "each point must be [x, y] with numeric coordinates"
    return None


def validate_rule_params(rule_type: str, params: dict[str, Any]) -> str | None:
    if rule_type not in SUPPORTED_RULE_TYPES:
        return f"Unsupported rule_type '{rule_type}'"
    if not isinstance(params, dict):
        return "params must be an object"

    if rule_type == "zone_enter":
        zone_id = params.get("zone_id")
        if not isinstance(zone_id, str) or not zone_id.strip():
            return "zone_enter requires non-empty 'zone_id'"

    if rule_type == "line_cross":
        line = params.get("line")
        if not isinstance(line, list) or len(line) != 2 or any(not _is_point(p) for p in line):
            return "line_cross requires 'line' with exactly two points [x, y]"

    if rule_type == "dwell_time":
        zone_id = params.get("zone_id")
        seconds = params.get("seconds")
        if not isinstance(zone_id, str) or not zone_id.strip():
            return "dwell_time requires non-empty 'zone_id'"
        if not isinstance(seconds, int) or seconds < 1:
            return "dwell_time requires integer 'seconds' >= 1"

    return None
