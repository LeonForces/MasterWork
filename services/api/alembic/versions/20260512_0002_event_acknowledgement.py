"""event acknowledgement fields

Revision ID: 20260512_0002
Revises: 20260307_0001
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260512_0002"
down_revision = "20260307_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("acknowledged_by", sa.String(length=36), nullable=True))
    op.create_index("ix_events_acknowledged_at", "events", ["acknowledged_at"])


def downgrade() -> None:
    op.drop_index("ix_events_acknowledged_at", table_name="events")
    op.drop_column("events", "acknowledged_by")
    op.drop_column("events", "acknowledged_at")
