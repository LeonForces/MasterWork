from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

app = FastAPI(title="Webhook Mock", version="1.0.0")

RECEIVED_EVENTS: list[dict[str, Any]] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/events")
def receive_event(payload: dict[str, Any]) -> dict[str, Any]:
    RECEIVED_EVENTS.append(
        {
            "received_at": datetime.now(tz=timezone.utc).isoformat(),
            "payload": payload,
        }
    )
    return {"accepted": True}


@app.get("/events")
def get_events() -> dict[str, Any]:
    return {"count": len(RECEIVED_EVENTS), "items": RECEIVED_EVENTS[-100:]}
