from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, Text, and_, create_engine, or_, select, update

from app.settings import settings

metadata = MetaData()

event_outbox = Table(
    "event_outbox",
    metadata,
    Column("outbox_id", String(36), primary_key=True),
    Column("event_id", String(36), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("status", String(16), nullable=False),
    Column("retry_count", Integer, nullable=False),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("published_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

delivery_attempts = Table(
    "delivery_attempts",
    metadata,
    Column("attempt_id", String(36), primary_key=True),
    Column("event_id", String(36), nullable=False),
    Column("consumer_name", String(128), nullable=False),
    Column("status", String(16), nullable=False),
    Column("attempted_at", DateTime(timezone=True), nullable=False),
    Column("error_text", Text, nullable=True),
)

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def calc_next_retry(retry_count: int) -> datetime:
    # Exponential backoff, capped at 5 minutes.
    delay_seconds = min(300, 2 ** min(retry_count, 8))
    return now_utc() + timedelta(seconds=delay_seconds)


def fetch_publish_candidates(limit: int = 100) -> list[dict]:
    stmt = (
        select(event_outbox)
        .where(
            and_(
                event_outbox.c.status.in_(["pending", "retry"]),
                or_(event_outbox.c.next_retry_at.is_(None), event_outbox.c.next_retry_at <= now_utc()),
            )
        )
        .order_by(event_outbox.c.created_at.asc())
        .limit(limit)
    )
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


def mark_published(outbox_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            update(event_outbox)
            .where(event_outbox.c.outbox_id == outbox_id)
            .values(status="published", published_at=now_utc(), next_retry_at=None)
        )


def mark_retry(outbox_id: str, retry_count: int, terminal: bool) -> None:
    with engine.begin() as conn:
        conn.execute(
            update(event_outbox)
            .where(event_outbox.c.outbox_id == outbox_id)
            .values(
                status="failed" if terminal else "retry",
                retry_count=retry_count,
                next_retry_at=None if terminal else calc_next_retry(retry_count),
            )
        )


def log_delivery_attempt(event_id: str, consumer_name: str, status: str, error_text: str | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            delivery_attempts.insert().values(
                attempt_id=str(uuid4()),
                event_id=event_id,
                consumer_name=consumer_name,
                status=status,
                attempted_at=now_utc(),
                error_text=error_text,
            )
        )


def already_delivered(event_id: str, consumer_name: str) -> bool:
    stmt = (
        select(delivery_attempts.c.attempt_id)
        .where(
            and_(
                delivery_attempts.c.event_id == event_id,
                delivery_attempts.c.consumer_name == consumer_name,
                delivery_attempts.c.status == "success",
            )
        )
        .limit(1)
    )
    with engine.connect() as conn:
        return conn.execute(stmt).first() is not None
