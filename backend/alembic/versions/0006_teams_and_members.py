"""teams and team_members Phase 7 schema

Revision ID: 0006_teams_and_members
Revises: 0005_hints_and_writeups
Create Date: 2026-09-05 11:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_teams_and_members"
down_revision: Union[str, None] = "0005_hints_and_writeups"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add fields to teams table
    op.add_column("teams", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("teams", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.add_column("teams", sa.Column("college", sa.String(length=150), nullable=True))
    op.add_column("teams", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    # Backfill owner_id from captain_id
    op.execute("UPDATE teams SET owner_id = captain_id WHERE owner_id IS NULL")

    # Add indexes and constraints on teams
    with op.batch_alter_table("teams", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_teams_owner_id"), ["owner_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_teams_college"), ["college"], unique=False)
        batch_op.create_foreign_key("fk_teams_owner_id_users", "users", ["owner_id"], ["id"], ondelete="RESTRICT")

    # 2. Recreate team_members as a full model table
    op.drop_table("team_members")
    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user")
    )
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)


def downgrade() -> None:
    # Drop full team_members table
    op.drop_table("team_members")

    # Recreate association table
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

    # Revert teams columns
    with op.batch_alter_table("teams", schema=None) as batch_op:
        batch_op.drop_constraint("fk_teams_owner_id_users", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_teams_college"))
        batch_op.drop_index(batch_op.f("ix_teams_owner_id"))
        batch_op.drop_column("is_active")
        batch_op.drop_column("college")
        batch_op.drop_column("owner_id")
        batch_op.drop_column("description")
