"""solves ledger and submission constraints

Revision ID: 0003_solves
Revises: 0002_challenge_mgmt
Create Date: 2026-09-05 02:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_solves"
down_revision: Union[str, None] = "0002_challenge_mgmt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "solves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge_solve"),
    )
    op.create_index(op.f("ix_solves_id"), "solves", ["id"], unique=False)
    op.create_index(op.f("ix_solves_user_id"), "solves", ["user_id"], unique=False)
    op.create_index(op.f("ix_solves_challenge_id"), "solves", ["challenge_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_solves_challenge_id"), table_name="solves")
    op.drop_index(op.f("ix_solves_user_id"), table_name="solves")
    op.drop_index(op.f("ix_solves_id"), table_name="solves")
    op.drop_table("solves")
