from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Event, User, now_utc
from app.schemas import EventEvidenceOut, EventOut

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    camera_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> list[Event]:
    query = db.query(Event)
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    return query.order_by(Event.occurred_at.desc()).limit(limit).all()


@router.patch("/{event_id}/ack", response_model=EventOut)
def acknowledge_event(
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operator")),
) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.acknowledged_at:
        event.acknowledged_at = now_utc()
        event.acknowledged_by = user.user_id
        db.commit()
        db.refresh(event)
    return event


@router.get("/{event_id}/evidence", response_model=EventEvidenceOut)
def get_event_evidence(
    event_id: str,
    response: Response,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> EventEvidenceOut:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    response.headers["Content-Disposition"] = f'attachment; filename="event-{event.event_id}.json"'
    return EventEvidenceOut(
        event_id=event.event_id,
        camera_id=event.camera_id,
        track_id=event.track_id,
        rule_id=event.rule_id,
        event_type=event.event_type,
        severity=event.severity,
        occurred_at=event.occurred_at,
        confidence=event.confidence,
        snapshot_path=event.snapshot_path,
        dedup_key=event.dedup_key,
        attributes=event.attributes,
        status="acknowledged" if event.acknowledged_at else "open",
        acknowledged_at=event.acknowledged_at,
        acknowledged_by=event.acknowledged_by,
        exported_at=now_utc(),
    )
