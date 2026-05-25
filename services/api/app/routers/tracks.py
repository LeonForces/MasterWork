from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Track, User
from app.schemas import TrackOut

router = APIRouter(prefix="/api/v1/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackOut])
def list_tracks(
    camera_id: str | None = Query(default=None),
    object_class: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> list[Track]:
    query = db.query(Track)
    if camera_id:
        query = query.filter(Track.camera_id == camera_id)
    if object_class:
        query = query.filter(Track.object_class == object_class)
    return query.order_by(Track.last_seen_at.desc()).limit(limit).all()
