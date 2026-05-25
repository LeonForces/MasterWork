from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
os.environ["JWT_SECRET_KEY"] = "this_is_a_long_test_secret_key_32_chars_minimum"
os.environ["DEFAULT_ADMIN_USERNAME"] = "admin"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "admin12345"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import ensure_default_admin, ensure_default_roles  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
ensure_default_roles(db)
ensure_default_admin(db)
db.close()

client = TestClient(app)


def login(username: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()


def test_login_and_me() -> None:
    token = login("admin", "admin12345")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 200
    assert "admin" in response.json()["roles"]


def test_viewer_cannot_create_camera() -> None:
    admin_token = login("admin", "admin12345")
    create_user_response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token['access_token']}"},
        json={"username": "viewer_user", "password": "viewer12345", "roles": ["viewer"]},
    )
    assert create_user_response.status_code in (200, 409)

    viewer_token = login("viewer_user", "viewer12345")
    create_camera_response = client.post(
        "/api/v1/cameras",
        headers={"Authorization": f"Bearer {viewer_token['access_token']}"},
        json={
            "name": "cam-test",
            "rtsp_url": "sample.mp4",
            "status": "active",
            "fps_target": 5,
            "resolution": "640x480",
        },
    )
    assert create_camera_response.status_code == 403


def test_refresh_and_logout_revoke_token() -> None:
    token = login("admin", "admin12345")
    refresh_token = token["refresh_token"]

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout_response.status_code == 200

    second_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert second_refresh.status_code == 401


def test_zone_and_rule_validation() -> None:
    token = login("admin", "admin12345")
    headers = {"Authorization": f"Bearer {token['access_token']}"}

    camera_response = client.post(
        "/api/v1/cameras",
        headers=headers,
        json={
            "name": "validation-cam",
            "rtsp_url": "sample.mp4",
            "status": "active",
            "fps_target": 5,
            "resolution": "640x480",
        },
    )
    assert camera_response.status_code == 200
    camera_id = camera_response.json()["camera_id"]

    bad_zone = client.post(
        "/api/v1/zones",
        headers=headers,
        json={
            "camera_id": camera_id,
            "name": "bad-zone",
            "zone_type": "polygon",
            "geometry": {"points": [[1, 1], [2, 2]]},
        },
    )
    assert bad_zone.status_code == 400

    zone_response = client.post(
        "/api/v1/zones",
        headers=headers,
        json={
            "camera_id": camera_id,
            "name": "good-zone",
            "zone_type": "polygon",
            "geometry": {"points": [[1, 1], [10, 1], [10, 10], [1, 10]]},
        },
    )
    assert zone_response.status_code == 200
    zone_id = zone_response.json()["zone_id"]

    bad_dwell = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "camera_id": camera_id,
            "name": "bad-dwell",
            "rule_type": "dwell_time",
            "params": {"zone_id": zone_id, "seconds": 0},
            "severity": "high",
            "enabled": True,
        },
    )
    assert bad_dwell.status_code == 400

    bad_line = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "camera_id": camera_id,
            "name": "bad-line",
            "rule_type": "line_cross",
            "params": {"line": [[1, 1]]},
            "severity": "high",
            "enabled": True,
        },
    )
    assert bad_line.status_code == 400


def test_operator_can_delete_camera_zone_rule() -> None:
    admin = login("admin", "admin12345")
    headers = {"Authorization": f"Bearer {admin['access_token']}"}

    operator_create = client.post(
        "/api/v1/users",
        headers=headers,
        json={"username": "operator_user", "password": "operator12345", "roles": ["operator"]},
    )
    assert operator_create.status_code in (200, 409)
    operator = login("operator_user", "operator12345")
    operator_headers = {"Authorization": f"Bearer {operator['access_token']}"}

    camera_response = client.post(
        "/api/v1/cameras",
        headers=operator_headers,
        json={
            "name": "delete-cam",
            "rtsp_url": "sample.mp4",
            "status": "active",
            "fps_target": 5,
            "resolution": "640x480",
        },
    )
    assert camera_response.status_code == 200
    camera_id = camera_response.json()["camera_id"]

    zone_response = client.post(
        "/api/v1/zones",
        headers=operator_headers,
        json={
            "camera_id": camera_id,
            "name": "delete-zone",
            "zone_type": "polygon",
            "geometry": {"points": [[1, 1], [10, 1], [10, 10], [1, 10]]},
        },
    )
    assert zone_response.status_code == 200
    zone_id = zone_response.json()["zone_id"]

    rule_response = client.post(
        "/api/v1/rules",
        headers=operator_headers,
        json={
            "camera_id": camera_id,
            "name": "delete-rule",
            "rule_type": "zone_enter",
            "params": {"zone_id": zone_id},
            "severity": "high",
            "enabled": True,
        },
    )
    assert rule_response.status_code == 200
    rule_id = rule_response.json()["rule_id"]

    delete_rule = client.delete(f"/api/v1/rules/{rule_id}", headers=operator_headers)
    assert delete_rule.status_code == 204
    delete_zone = client.delete(f"/api/v1/zones/{zone_id}", headers=operator_headers)
    assert delete_zone.status_code == 204
    delete_camera = client.delete(f"/api/v1/cameras/{camera_id}", headers=operator_headers)
    assert delete_camera.status_code == 204
