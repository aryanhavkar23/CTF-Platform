"""anti_cheat and security_events Phase 14 schema

Revision ID: 0012_anti_cheat_and_security_events
Revises: 0011_notifications
Create Date: 2026-09-14 07:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012_anti_cheat_and_security_events"
down_revision: Union[str, None] = "0011_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. security_events
    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("challenge_id", sa.Uuid(), sa.ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_security_events_id", "security_events", ["id"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_team_id", "security_events", ["team_id"])
    op.create_index("ix_security_events_event_id", "security_events", ["event_id"])
    op.create_index("ix_security_events_challenge_id", "security_events", ["challenge_id"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_status", "security_events", ["status"])
    op.create_index("ix_security_events_ip_address", "security_events", ["ip_address"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])

    # 2. security_event_reviews
    op.create_table(
        "security_event_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("security_event_id", sa.Uuid(), sa.ForeignKey("security_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_security_event_reviews_id", "security_event_reviews", ["id"])
    op.create_index("ix_security_event_reviews_security_event_id", "security_event_reviews", ["security_event_id"])
    op.create_index("ix_security_event_reviews_reviewer_id", "security_event_reviews", ["reviewer_id"])
    op.create_index("ix_security_event_reviews_created_at", "security_event_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_table("security_event_reviews")
    op.drop_table("security_events")
