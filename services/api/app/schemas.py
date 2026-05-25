from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    roles: list[str]


class UserOut(BaseModel):
    user_id: str
    username: str
    roles: list[str]
    is_active: bool


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=8)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])


class CameraBase(BaseModel):
    name: str
    rtsp_url: str
    status: str = "active"
    fps_target: int = 10
    resolution: str = "1280x720"


class CameraCreate(CameraBase):
    pass


class CameraPatch(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    status: str | None = None
    fps_target: int | None = None
    resolution: str | None = None


class CameraOut(CameraBase):
    camera_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneBase(BaseModel):
    camera_id: str
    name: str
    geometry: dict[str, Any]
    zone_type: str


class ZoneCreate(ZoneBase):
    pass


class ZonePatch(BaseModel):
    name: str | None = None
    geometry: dict[str, Any] | None = None
    zone_type: str | None = None


class ZoneOut(ZoneBase):
    zone_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleBase(BaseModel):
    camera_id: str
    name: str
    rule_type: str
    params: dict[str, Any]
    severity: str = "medium"
    enabled: bool = True


class RuleCreate(RuleBase):
    pass


class RulePatch(BaseModel):
    name: str | None = None
    params: dict[str, Any] | None = None
    severity: str | None = None
    enabled: bool | None = None


class RuleOut(RuleBase):
    rule_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventOut(BaseModel):
    event_id: str
    camera_id: str
    track_id: str
    rule_id: str | None
    event_type: str
    severity: str
    occurred_at: datetime
    confidence: float
    snapshot_path: str | None
    dedup_key: str
    attributes: dict[str, Any]
    acknowledged_at: datetime | None
    acknowledged_by: str | None

    model_config = ConfigDict(from_attributes=True)


class EventEvidenceOut(BaseModel):
    schema_version: int = 1
    event_id: str
    camera_id: str
    track_id: str
    rule_id: str | None
    event_type: str
    severity: str
    occurred_at: datetime
    confidence: float
    snapshot_path: str | None
    dedup_key: str
    attributes: dict[str, Any]
    status: str
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    exported_at: datetime


class TrackOut(BaseModel):
    track_id: str
    camera_id: str
    object_class: str
    started_at: datetime
    last_seen_at: datetime
    last_bbox: list[float]
    state: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
