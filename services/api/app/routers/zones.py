from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Camera, User, Zone
from app.schemas import ZoneCreate, ZoneOut, ZonePatch
from app.validation import validate_geometry

router = APIRouter(prefix="/api/v1/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut])
def list_zones(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> list[Zone]:
    return db.query(Zone).order_by(Zone.created_at.desc()).all()


@router.post("", response_model=ZoneOut)
def create_zone(
    payload: ZoneCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Zone:
    camera = db.get(Camera, payload.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    geometry_error = validate_geometry(payload.zone_type, payload.geometry)
    if geometry_error:
        raise HTTPException(status_code=400, detail=geometry_error)
    zone = Zone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/{zone_id}", response_model=ZoneOut)
def patch_zone(
    zone_id: str,
    payload: ZonePatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Zone:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    next_zone_type = payload.zone_type if payload.zone_type is not None else zone.zone_type
    next_geometry = payload.geometry if payload.geometry is not None else zone.geometry
    geometry_error = validate_geometry(next_zone_type, next_geometry)
    if geometry_error:
        raise HTTPException(status_code=400, detail=geometry_error)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=204)
def delete_zone(
    zone_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Response:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(zone)
    db.commit()
    return Response(status_code=204)
