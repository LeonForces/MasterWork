from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.settings import settings

metadata = MetaData()

cameras = Table(
    "cameras",
    metadata,
    Column("camera_id", String(36), primary_key=True),
    Column("name", String(128), nullable=False),
    Column("rtsp_url", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("fps_target", Integer, nullable=False),
    Column("resolution", String(32), nullable=False),
)

zones = Table(
    "zones",
    metadata,
    Column("zone_id", String(36), primary_key=True),
    Column("camera_id", String(36), nullable=False),
    Column("name", String(128), nullable=False),
    Column("geometry", JSON, nullable=False),
    Column("zone_type", String(32), nullable=False),
)

rules = Table(
    "rules",
    metadata,
    Column("rule_id", String(36), primary_key=True),
    Column("camera_id", String(36), nullable=False),
    Column("name", String(128), nullable=False),
    Column("rule_type", String(32), nullable=False),
    Column("params", JSON, nullable=False),
    Column("severity", String(16), nullable=False),
    Column("enabled", Boolean, nullable=False),
)

tracks = Table(
    "tracks",
    metadata,
    Column("track_id", String(64), primary_key=True),
    Column("camera_id", String(36), primary_key=True),
    Column("object_class", String(32), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_bbox", JSON, nullable=False),
    Column("state", JSON, nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("event_id", String(36), primary_key=True),
    Column("camera_id", String(36), nullable=False),
    Column("track_id", String(64), nullable=False),
    Column("rule_id", String(36), nullable=True),
    Column("event_type", String(32), nullable=False),
    Column("severity", String(16), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("confidence", Float, nullable=False),
    Column("snapshot_path", Text, nullable=True),
    Column("dedup_key", String(255), nullable=False),
    Column("attributes", JSON, nullable=False),
)

event_outbox = Table(
    "event_outbox",
    metadata,
    Column("outbox_id", String(36), primary_key=True),
    Column("event_id", String(36), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("status", String(16), nullable=False),
    Column("retry_count", Integer, nullable=False, default=0),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def list_active_cameras() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(select(cameras).where(cameras.c.status == "active")).mappings().all()
    return [dict(row) for row in rows]


def get_camera_rules_and_zones(camera_id: str) -> tuple[list[dict], list[dict]]:
    with engine.connect() as conn:
        rule_rows = conn.execute(
            select(rules).where(and_(rules.c.camera_id == camera_id, rules.c.enabled.is_(True)))
        ).mappings().all()
        zone_rows = conn.execute(select(zones).where(zones.c.camera_id == camera_id)).mappings().all()
    return [dict(row) for row in rule_rows], [dict(row) for row in zone_rows]


def upsert_track(camera_id: str, track: dict) -> None:
    ts = now_utc()
    state = dict(track.get("state") or {})
    state["confidence"] = float(track.get("confidence", 0.0))
    payload = {
        "track_id": str(track["track_id"]),
        "camera_id": camera_id,
        "object_class": track["object_class"],
        "started_at": track.get("started_at", ts),
        "last_seen_at": ts,
        "last_bbox": track["bbox"],
        "state": state,
    }
    stmt = pg_insert(tracks).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=[tracks.c.track_id, tracks.c.camera_id],
        set_={
            "object_class": payload["object_class"],
            "last_seen_at": payload["last_seen_at"],
            "last_bbox": payload["last_bbox"],
            "state": payload["state"],
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def persist_events(camera_id: str, events_payload: list[dict]) -> int:
    inserted = 0
    with engine.begin() as conn:
        for event in events_payload:
            event_id = str(uuid4())
            event_row = {
                "event_id": event_id,
                "camera_id": camera_id,
                "track_id": event["track_id"],
                "rule_id": event.get("rule_id"),
                "event_type": event["event_type"],
                "severity": event["severity"],
                "occurred_at": event["occurred_at"],
                "confidence": event["confidence"],
                "snapshot_path": event.get("snapshot_path"),
                "dedup_key": event["dedup_key"],
                "attributes": event.get("attributes", {}),
            }
            try:
                conn.execute(events.insert().values(event_row))
            except IntegrityError:
                # dedup_key conflict
                continue

            payload = {
                "schema_version": 1,
                "event_id": event_id,
                "event_type": event["event_type"],
                "camera_id": camera_id,
                "track_id": event["track_id"],
                "object_class": event["object_class"],
                "confidence": event["confidence"],
                "occurred_at": event["occurred_at"].isoformat(),
                "zone_id": event.get("zone_id"),
                "rule_id": event.get("rule_id"),
                "severity": event["severity"],
                "snapshot_path": event.get("snapshot_path"),
                "dedup_key": event["dedup_key"],
                "attributes": event.get("attributes", {}),
            }
            conn.execute(
                event_outbox.insert().values(
                    outbox_id=str(uuid4()),
                    event_id=event_id,
                    payload=payload,
                    status="pending",
                    retry_count=0,
                    next_retry_at=None,
                    created_at=now_utc(),
                )
            )
            inserted += 1
    return inserted
