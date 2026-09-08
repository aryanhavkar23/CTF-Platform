"""user profiles and activity Phase 9 schema

Revision ID: 0008_user_profiles_and_activity
Revises: 0007_events_and_participation
Create Date: 2026-09-06 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_user_profiles_and_activity"
down_revision: Union[str, None] = "0007_events_and_participation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update users table with profile fields
    op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=500), nullable=True))

    # 2. Create user_activities table
    op.create_table(
        "user_activities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_user_activities_user_id", "user_activities", ["user_id"])
    op.create_index("ix_user_activities_activity_type", "user_activities", ["activity_type"])
    op.create_index("ix_user_activities_reference_id", "user_activities", ["reference_id"])
    op.create_index("ix_user_activities_created_at", "user_activities", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_activities_created_at", table_name="user_activities")
    op.drop_index("ix_user_activities_reference_id", table_name="user_activities")
    op.drop_index("ix_user_activities_activity_type", table_name="user_activities")
    op.drop_index("ix_user_activities_user_id", table_name="user_activities")
    op.drop_table("user_activities")

    op.drop_column("users", "bio")
    op.drop_column("users", "name")
