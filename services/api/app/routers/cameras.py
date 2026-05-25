from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Camera, User
from app.schemas import CameraCreate, CameraOut, CameraPatch

router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
def list_cameras(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> list[Camera]:
    return db.query(Camera).order_by(Camera.created_at.desc()).all()


@router.post("", response_model=CameraOut)
def create_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Camera:
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.patch("/{camera_id}", response_model=CameraOut)
def patch_camera(
    camera_id: str,
    payload: CameraPatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Camera:
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, key, value)
    camera.updated_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_id}", status_code=204)
def delete_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Response:
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()
    return Response(status_code=204)
