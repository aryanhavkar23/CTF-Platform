"""badges and achievements Phase 10 schema

Revision ID: 0009_badges_and_achievements
Revises: 0008_user_profiles_and_activity
Create Date: 2026-09-06 22:15:00.000000

"""
import uuid
from typing import Sequence, Union
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_badges_and_achievements"
down_revision: Union[str, None] = "0008_user_profiles_and_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_BADGES = [
    {
        "id": uuid.uuid4(),
        "name": "First Blood",
        "slug": "first-blood",
        "description": "Solved your very first CTF challenge.",
        "icon": "drop-crosshair",
        "criteria_type": "first_solve",
        "criteria_value": 1,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Novice Hacker",
        "slug": "novice-hacker",
        "description": "Solved 5 challenges across the platform.",
        "icon": "terminal",
        "criteria_type": "solve_count",
        "criteria_value": 5,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Cyber Explorer",
        "slug": "cyber-explorer",
        "description": "Solved challenges across at least 3 distinct security categories.",
        "icon": "compass",
        "criteria_type": "category_solves",
        "criteria_value": 3,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "CTF Grinder",
        "slug": "ctf-grinder",
        "description": "Solved 25 challenges across the platform.",
        "icon": "cpu",
        "criteria_type": "solve_count",
        "criteria_value": 25,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Point Hunter",
        "slug": "point-hunter",
        "description": "Accumulated 1,000 or more points.",
        "icon": "target",
        "criteria_type": "points_reached",
        "criteria_value": 1000,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Streak Starter",
        "slug": "streak-starter",
        "description": "Maintained an active CTF streak of 3 consecutive days.",
        "icon": "flame",
        "criteria_type": "streak_days",
        "criteria_value": 3,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Weekly Warrior",
        "slug": "weekly-warrior",
        "description": "Maintained an active CTF streak of 7 consecutive days.",
        "icon": "shield",
        "criteria_type": "streak_days",
        "criteria_value": 7,
        "is_active": True,
    },
    {
        "id": uuid.uuid4(),
        "name": "Event Participant",
        "slug": "event-participant",
        "description": "Registered and participated in an official live CTF competition.",
        "icon": "trophy",
        "criteria_type": "event_participation",
        "criteria_value": 1,
        "is_active": True,
    },
]


def upgrade() -> None:
    # 1. Create badges table
    badges_table = op.create_table(
        "badges",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("icon", sa.String(length=255), nullable=False),
        sa.Column("criteria_type", sa.String(length=50), nullable=False),
        sa.Column("criteria_value", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_badges_id", "badges", ["id"])
    op.create_index("ix_badges_slug", "badges", ["slug"], unique=True)
    op.create_index("ix_badges_criteria_type", "badges", ["criteria_type"])
    op.create_index("ix_badges_is_active", "badges", ["is_active"])

    # 2. Create user_badges table
    op.create_table(
        "user_badges",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_id", sa.Uuid(), sa.ForeignKey("badges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    op.create_index("ix_user_badges_id", "user_badges", ["id"])
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])
    op.create_index("ix_user_badges_awarded_at", "user_badges", ["awarded_at"])

    # 3. Seed standard initial badge definitions
    now_utc = datetime.now(timezone.utc)
    seed_data = [
        {
            **badge,
            "created_at": now_utc,
            "updated_at": now_utc,
        }
        for badge in INITIAL_BADGES
    ]
    op.bulk_insert(badges_table, seed_data)


def downgrade() -> None:
    op.drop_index("ix_user_badges_awarded_at", table_name="user_badges")
    op.drop_index("ix_user_badges_badge_id", table_name="user_badges")
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_index("ix_user_badges_id", table_name="user_badges")
    op.drop_table("user_badges")

    op.drop_index("ix_badges_is_active", table_name="badges")
    op.drop_index("ix_badges_criteria_type", table_name="badges")
    op.drop_index("ix_badges_slug", table_name="badges")
    op.drop_index("ix_badges_id", table_name="badges")
    op.drop_table("badges")
