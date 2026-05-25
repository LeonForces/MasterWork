from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Camera, Role, Rule, User, UserRole, Zone
from app.security import get_password_hash


def ensure_default_roles(db: Session) -> None:
    for role_name in ("admin", "operator", "viewer"):
        existing = db.get(Role, role_name)
        if not existing:
            db.add(Role(role_name=role_name))
    db.commit()


def ensure_default_admin(db: Session) -> None:
    user = db.query(User).filter(User.username == settings.default_admin_username).first()
    if not user:
        user = User(
            username=settings.default_admin_username,
            hashed_password=get_password_hash(settings.default_admin_password),
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.user_id, role_name="admin"))
        db.commit()
        return

    has_admin_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.user_id, UserRole.role_name == "admin")
        .first()
    )
    if not has_admin_role:
        db.add(UserRole(user_id=user.user_id, role_name="admin"))
        db.commit()


def _resolution_to_points(resolution: str) -> list[list[int]]:
    try:
        width, height = [int(part.strip()) for part in resolution.lower().split("x", maxsplit=1)]
    except (TypeError, ValueError):
        width, height = 640, 512
    return [[0, 0], [width, 0], [width, height], [0, height]]


def ensure_demo_drone_camera(db: Session) -> None:
    if not settings.demo_drone_enabled:
        return

    if settings.demo_drone_exclusive:
        db.query(Camera).filter(
            Camera.name != settings.demo_drone_camera_name,
            Camera.status == "active",
        ).update({"status": "inactive"}, synchronize_session=False)

    camera = db.query(Camera).filter(Camera.name == settings.demo_drone_camera_name).first()
    if not camera:
        camera = Camera(
            name=settings.demo_drone_camera_name,
            rtsp_url=settings.demo_drone_source,
            status="active",
            fps_target=settings.demo_drone_fps_target,
            resolution=settings.demo_drone_resolution,
        )
        db.add(camera)
        db.flush()
    else:
        camera.rtsp_url = settings.demo_drone_source
        camera.status = "active"
        camera.fps_target = settings.demo_drone_fps_target
        camera.resolution = settings.demo_drone_resolution

    zone_name = "demo-full-frame-zone"
    zone = db.query(Zone).filter(Zone.camera_id == camera.camera_id, Zone.name == zone_name).first()
    geometry = {"points": _resolution_to_points(settings.demo_drone_resolution)}
    if not zone:
        zone = Zone(
            camera_id=camera.camera_id,
            name=zone_name,
            geometry=geometry,
            zone_type="polygon",
        )
        db.add(zone)
        db.flush()
    else:
        zone.geometry = geometry
        zone.zone_type = "polygon"

    rule_name = "demo-drone-zone-enter"
    rule = db.query(Rule).filter(Rule.camera_id == camera.camera_id, Rule.name == rule_name).first()
    if not rule:
        rule = Rule(
            camera_id=camera.camera_id,
            name=rule_name,
            rule_type="zone_enter",
            params={"zone_id": zone.zone_id},
            severity="high",
            enabled=True,
        )
        db.add(rule)
    else:
        rule.params = {"zone_id": zone.zone_id}
        rule.severity = "high"
        rule.enabled = True

    db.commit()
