"""live challenge instances Phase 15 schema

Revision ID: 0013_live_challenge_instances
Revises: 0012_anti_cheat_and_security_events
Create Date: 2026-09-14 08:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013_live_challenge_instances"
down_revision: Union[str, None] = "0012_anti_cheat_and_security_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend challenges table with live instance configuration
    with op.batch_alter_table("challenges") as batch_op:
        batch_op.add_column(sa.Column("container_port", sa.Integer(), nullable=True, server_default="80"))
        batch_op.add_column(sa.Column("protocol", sa.String(length=20), nullable=False, server_default="http"))
        batch_op.add_column(sa.Column("instance_mode", sa.String(length=20), nullable=False, server_default="per_user"))
        batch_op.add_column(sa.Column("cpu_limit", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("memory_limit", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"))
        batch_op.add_column(sa.Column("healthcheck_path", sa.String(length=255), nullable=True, server_default="/"))

    # 2. Create challenge_instances table
    op.create_table(
        "challenge_instances",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("challenge_id", sa.Uuid(), sa.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("container_id", sa.String(length=128), nullable=True),
        sa.Column("container_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("internal_port", sa.Integer(), server_default="80", nullable=False),
        sa.Column("external_port", sa.Integer(), nullable=True),
        sa.Column("external_host", sa.String(length=255), server_default="localhost", nullable=False),
        sa.Column("url", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_challenge_instances_id", "challenge_instances", ["id"])
    op.create_index("ix_challenge_instances_challenge_id", "challenge_instances", ["challenge_id"])
    op.create_index("ix_challenge_instances_user_id", "challenge_instances", ["user_id"])
    op.create_index("ix_challenge_instances_team_id", "challenge_instances", ["team_id"])
    op.create_index("ix_challenge_instances_event_id", "challenge_instances", ["event_id"])
    op.create_index("ix_challenge_instances_container_id", "challenge_instances", ["container_id"])
    op.create_index("ix_challenge_instances_container_name", "challenge_instances", ["container_name"], unique=True)
    op.create_index("ix_challenge_instances_status", "challenge_instances", ["status"])
    op.create_index("ix_challenge_instances_external_port", "challenge_instances", ["external_port"])
    op.create_index("ix_challenge_instances_expires_at", "challenge_instances", ["expires_at"])
    op.create_index("ix_challenge_instances_challenge_user", "challenge_instances", ["challenge_id", "user_id"])
    op.create_index("ix_challenge_instances_challenge_team", "challenge_instances", ["challenge_id", "team_id"])


def downgrade() -> None:
    op.drop_table("challenge_instances")
    with op.batch_alter_table("challenges") as batch_op:
        batch_op.drop_column("healthcheck_path")
        batch_op.drop_column("ttl_seconds")
        batch_op.drop_column("memory_limit")
        batch_op.drop_column("cpu_limit")
        batch_op.drop_column("instance_mode")
        batch_op.drop_column("protocol")
        batch_op.drop_column("container_port")
