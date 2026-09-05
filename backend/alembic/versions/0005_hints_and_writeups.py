"""hints title and writeups title and hint usage table

Revision ID: 0005_hints_and_writeups
Revises: 0004_leaderboard_indexes
Create Date: 2026-09-05 11:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_hints_and_writeups"
down_revision: Union[str, None] = "0004_leaderboard_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add title to challenge_hints
    op.add_column(
        "challenge_hints",
        sa.Column("title", sa.String(length=150), server_default="Hint", nullable=False)
    )

    # 2. Add title to challenge_writeups
    op.add_column(
        "challenge_writeups",
        sa.Column("title", sa.String(length=150), server_default="Official Writeup", nullable=False)
    )

    # 3. Create hint_usage table
    op.create_table(
        "hint_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("hint_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("points_deducted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hint_id"], ["challenge_hints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "hint_id", name="uq_user_hint_usage")
    )
    op.create_index(op.f("ix_hint_usage_id"), "hint_usage", ["id"], unique=False)
    op.create_index(op.f("ix_hint_usage_user_id"), "hint_usage", ["user_id"], unique=False)
    op.create_index(op.f("ix_hint_usage_hint_id"), "hint_usage", ["hint_id"], unique=False)
    op.create_index(op.f("ix_hint_usage_challenge_id"), "hint_usage", ["challenge_id"], unique=False)
    op.create_index("ix_hint_usage_user_challenge", "hint_usage", ["user_id", "challenge_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_hint_usage_user_challenge", table_name="hint_usage")
    op.drop_index(op.f("ix_hint_usage_challenge_id"), table_name="hint_usage")
    op.drop_index(op.f("ix_hint_usage_hint_id"), table_name="hint_usage")
    op.drop_index(op.f("ix_hint_usage_user_id"), table_name="hint_usage")
    op.drop_index(op.f("ix_hint_usage_id"), table_name="hint_usage")
    op.drop_table("hint_usage")
    op.drop_column("challenge_writeups", "title")
    op.drop_column("challenge_hints", "title")
