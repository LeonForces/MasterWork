from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import Base, engine, get_db
from app.metrics import metrics_middleware, metrics_response
from app.routers import auth, cameras, demo, events, rules, tracks, users, zones
from app.seed import ensure_default_admin, ensure_default_roles, ensure_demo_drone_camera

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        ensure_default_roles(db)
        ensure_default_admin(db)
        ensure_demo_drone_camera(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.middleware("http")(metrics_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cameras.router)
app.include_router(zones.router)
app.include_router(rules.router)
app.include_router(events.router)
app.include_router(tracks.router)
app.include_router(demo.router)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return metrics_response()
