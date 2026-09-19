"""Remove Docker infrastructure: drop challenge_instances table, strip Docker columns from challenges, add external_url.

Revision ID: 0016_remove_docker_add_external_url
Revises: 0015_user_oauth_and_auth_extensions
Create Date: 2026-09-17 08:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0016_remove_docker_add_external_url"
down_revision: Union[str, None] = "0015_user_oauth_and_auth_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the challenge_instances table (Docker container tracking)
    op.drop_table("challenge_instances")

    # 2. Remove Docker-specific columns from challenges table
    with op.batch_alter_table("challenges") as batch_op:
        batch_op.drop_column("is_live_instance")
        batch_op.drop_column("docker_image")
        batch_op.drop_column("container_port")
        batch_op.drop_column("protocol")
        batch_op.drop_column("instance_mode")
        batch_op.drop_column("cpu_limit")
        batch_op.drop_column("memory_limit")
        batch_op.drop_column("ttl_seconds")
        batch_op.drop_column("healthcheck_path")
        batch_op.drop_column("challenge_type")
        # 3. Add external_url column for pre-hosted challenge links
        batch_op.add_column(sa.Column("external_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    # Restore Docker columns (best-effort; no data is recovered)
    with op.batch_alter_table("challenges") as batch_op:
        batch_op.drop_column("external_url")
        batch_op.add_column(sa.Column("challenge_type", sa.String(length=20), nullable=False, server_default="static"))
        batch_op.add_column(sa.Column("healthcheck_path", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"))
        batch_op.add_column(sa.Column("memory_limit", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("cpu_limit", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("instance_mode", sa.String(length=20), nullable=False, server_default="per_user"))
        batch_op.add_column(sa.Column("protocol", sa.String(length=20), nullable=False, server_default="http"))
        batch_op.add_column(sa.Column("container_port", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("docker_image", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_live_instance", sa.Boolean(), nullable=False, server_default="false"))

    # Recreate challenge_instances table
    op.create_table(
        "challenge_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("container_id", sa.String(length=128), nullable=True),
        sa.Column("container_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("internal_port", sa.Integer(), nullable=False),
        sa.Column("external_port", sa.Integer(), nullable=True),
        sa.Column("external_host", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
