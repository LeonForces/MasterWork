from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
os.environ["JWT_SECRET_KEY"] = "this_is_a_long_test_secret_key_32_chars_minimum"
os.environ["DEFAULT_ADMIN_USERNAME"] = "admin"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "admin12345"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Event, now_utc  # noqa: E402
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


def _headers() -> dict[str, str]:
    token = login("admin", "admin12345")
    return {"Authorization": f"Bearer {token['access_token']}"}


def _create_event(headers: dict[str, str]) -> str:
    camera_response = client.post(
        "/api/v1/cameras",
        headers=headers,
        json={
            "name": f"event-cam-{uuid4()}",
            "rtsp_url": "sample.mp4",
            "status": "active",
            "fps_target": 5,
            "resolution": "640x480",
        },
    )
    assert camera_response.status_code == 200
    camera_id = camera_response.json()["camera_id"]

    db = SessionLocal()
    try:
        event = Event(
            camera_id=camera_id,
            track_id="trk-evidence",
            rule_id=None,
            event_type="drone_detected",
            severity="high",
            occurred_at=now_utc(),
            confidence=0.94,
            snapshot_path=None,
            dedup_key=f"test-evidence-{uuid4()}",
            attributes={"object_class": "drone", "bbox": [0.52, 0.28, 0.24, 0.28]},
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.event_id
    finally:
        db.close()


def test_acknowledge_event_persists_and_evidence_exports() -> None:
    headers = _headers()
    event_id = _create_event(headers)

    ack_response = client.patch(f"/api/v1/events/{event_id}/ack", headers=headers, json={})
    assert ack_response.status_code == 200
    ack_payload = ack_response.json()
    assert ack_payload["acknowledged_at"] is not None
    assert ack_payload["acknowledged_by"] is not None

    list_response = client.get("/api/v1/events?limit=1000", headers=headers)
    assert list_response.status_code == 200
    listed_event = next(item for item in list_response.json() if item["event_id"] == event_id)
    assert listed_event["acknowledged_at"] == ack_payload["acknowledged_at"]

    evidence_response = client.get(f"/api/v1/events/{event_id}/evidence", headers=headers)
    assert evidence_response.status_code == 200
    assert f"event-{event_id}.json" in evidence_response.headers["content-disposition"]
    evidence_payload = evidence_response.json()
    assert evidence_payload["event_id"] == event_id
    assert evidence_payload["status"] == "acknowledged"
    assert evidence_payload["attributes"]["object_class"] == "drone"
