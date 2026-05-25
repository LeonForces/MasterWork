"""initial schema

Revision ID: 20260307_0001
Revises:
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260307_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=128), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "roles",
        sa.Column("role_name", sa.String(length=32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_name", sa.String(length=32), sa.ForeignKey("roles.role_name", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("token_id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    op.create_table(
        "cameras",
        sa.Column("camera_id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("rtsp_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fps_target", sa.Integer(), nullable=False),
        sa.Column("resolution", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cameras_status", "cameras", ["status"])

    op.create_table(
        "zones",
        sa.Column("zone_id", sa.String(length=36), primary_key=True),
        sa.Column("camera_id", sa.String(length=36), sa.ForeignKey("cameras.camera_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.Column("zone_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_zones_camera_id", "zones", ["camera_id"])

    op.create_table(
        "rules",
        sa.Column("rule_id", sa.String(length=36), primary_key=True),
        sa.Column("camera_id", sa.String(length=36), sa.ForeignKey("cameras.camera_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rules_camera_id", "rules", ["camera_id"])

    op.create_table(
        "tracks",
        sa.Column("track_id", sa.String(length=64), primary_key=True),
        sa.Column("camera_id", sa.String(length=36), sa.ForeignKey("cameras.camera_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("object_class", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_bbox", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
    )

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=36), primary_key=True),
        sa.Column("camera_id", sa.String(length=36), sa.ForeignKey("cameras.camera_id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("rules.rule_id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("snapshot_path", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.String(length=255), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.UniqueConstraint("dedup_key", name="uq_events_dedup_key"),
    )
    op.create_index("ix_events_camera_id", "events", ["camera_id"])
    op.create_index("ix_events_track_id", "events", ["track_id"])
    op.create_index("ix_events_rule_id", "events", ["rule_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"])

    op.create_table(
        "event_outbox",
        sa.Column("outbox_id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), sa.ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_outbox_event_id", "event_outbox", ["event_id"])
    op.create_index("ix_event_outbox_status", "event_outbox", ["status"])
    op.create_index("ix_event_outbox_next_retry_at", "event_outbox", ["next_retry_at"])

    op.create_table(
        "delivery_attempts",
        sa.Column("attempt_id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_delivery_attempts_event_id", "delivery_attempts", ["event_id"])
    op.create_index("ix_delivery_attempts_consumer_name", "delivery_attempts", ["consumer_name"])


def downgrade() -> None:
    op.drop_index("ix_delivery_attempts_consumer_name", table_name="delivery_attempts")
    op.drop_index("ix_delivery_attempts_event_id", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")
    op.drop_index("ix_event_outbox_next_retry_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_status", table_name="event_outbox")
    op.drop_index("ix_event_outbox_event_id", table_name="event_outbox")
    op.drop_table("event_outbox")
    op.drop_index("ix_events_occurred_at", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_rule_id", table_name="events")
    op.drop_index("ix_events_track_id", table_name="events")
    op.drop_index("ix_events_camera_id", table_name="events")
    op.drop_table("events")
    op.drop_table("tracks")
    op.drop_index("ix_rules_camera_id", table_name="rules")
    op.drop_table("rules")
    op.drop_index("ix_zones_camera_id", table_name="zones")
    op.drop_table("zones")
    op.drop_index("ix_cameras_status", table_name="cameras")
    op.drop_table("cameras")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
