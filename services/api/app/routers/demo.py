from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.deps import require_roles
from app.models import User

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.get("/drone-video")
def get_demo_drone_video(
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> FileResponse:
    video_path = Path(settings.demo_drone_source)
    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail=f"Demo video not found: {video_path}")
    return FileResponse(path=video_path, media_type="video/mp4", filename=video_path.name)
