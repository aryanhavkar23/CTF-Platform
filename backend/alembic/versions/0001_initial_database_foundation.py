"""initial database foundation

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-04 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("student", "moderator", "admin", name="userrole", native_enum=False, length=20), nullable=False),
        sa.Column("college", sa.String(length=150), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    # 2. teams table
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("captain_id", sa.Uuid(), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["captain_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=True)
    op.create_index(op.f("ix_teams_invite_code"), "teams", ["invite_code"], unique=True)
    op.create_index(op.f("ix_teams_captain_id"), "teams", ["captain_id"], unique=False)

    # 3. team_members association table
    op.create_table(
        "team_members",
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
        sa.UniqueConstraint("user_id", name="uq_team_members_user_id"),
    )

    # 4. categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)

    # 5. challenges table
    op.create_table(
        "challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty", sa.Enum("easy", "medium", "hard", "insane", name="challengedifficulty", native_enum=False, length=20), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("flag_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("challenge_type", sa.Enum("static", "live", name="challengetype", native_enum=False, length=20), nullable=False),
        sa.Column("file_urls", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("points >= 0", name="check_positive_points"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_challenges_id"), "challenges", ["id"], unique=False)
    op.create_index(op.f("ix_challenges_title"), "challenges", ["title"], unique=True)
    op.create_index(op.f("ix_challenges_category_id"), "challenges", ["category_id"], unique=False)
    op.create_index(op.f("ix_challenges_difficulty"), "challenges", ["difficulty"], unique=False)
    op.create_index(op.f("ix_challenges_is_active"), "challenges", ["is_active"], unique=False)

    # 6. events table
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_scoreboard_frozen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_time > start_time", name="check_event_time_order"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_id"), "events", ["id"], unique=False)
    op.create_index(op.f("ix_events_name"), "events", ["name"], unique=True)
    op.create_index(op.f("ix_events_start_time"), "events", ["start_time"], unique=False)
    op.create_index(op.f("ix_events_end_time"), "events", ["end_time"], unique=False)

    # 7. event_challenges association table
    op.create_table(
        "event_challenges",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("points_override", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "challenge_id"),
    )

    # 8. submissions table
    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_flag_hash", sa.String(length=255), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("points_awarded", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submissions_id"), "submissions", ["id"], unique=False)
    op.create_index(op.f("ix_submissions_user_id"), "submissions", ["user_id"], unique=False)
    op.create_index(op.f("ix_submissions_team_id"), "submissions", ["team_id"], unique=False)
    op.create_index(op.f("ix_submissions_challenge_id"), "submissions", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_submissions_event_id"), "submissions", ["event_id"], unique=False)
    op.create_index(op.f("ix_submissions_is_correct"), "submissions", ["is_correct"], unique=False)
    op.create_index("idx_submission_user_challenge_correct", "submissions", ["user_id", "challenge_id", "is_correct"], unique=False)
    op.create_index("idx_submission_team_challenge_correct", "submissions", ["team_id", "challenge_id", "is_correct"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_submission_team_challenge_correct", table_name="submissions")
    op.drop_index("idx_submission_user_challenge_correct", table_name="submissions")
    op.drop_index(op.f("ix_submissions_is_correct"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_event_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_challenge_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_team_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_user_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_id"), table_name="submissions")
    op.drop_table("submissions")

    op.drop_table("event_challenges")

    op.drop_index(op.f("ix_events_end_time"), table_name="events")
    op.drop_index(op.f("ix_events_start_time"), table_name="events")
    op.drop_index(op.f("ix_events_name"), table_name="events")
    op.drop_index(op.f("ix_events_id"), table_name="events")
    op.drop_table("events")

    op.drop_index(op.f("ix_challenges_is_active"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_difficulty"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_category_id"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_title"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_id"), table_name="challenges")
    op.drop_table("challenges")

    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")

    op.drop_table("team_members")

    op.drop_index(op.f("ix_teams_captain_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_invite_code"), table_name="teams")
    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_table("teams")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
