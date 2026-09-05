"""leaderboard performance indexes

Revision ID: 0004_leaderboard_indexes
Revises: 0003_solves
Create Date: 2026-09-05 10:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_leaderboard_indexes"
down_revision: Union[str, None] = "0003_solves"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_solves_created_at"),
        "solves",
        ["created_at"],
        unique=False
    )
    op.create_index(
        op.f("ix_users_college"),
        "users",
        ["college"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_college"), table_name="users")
    op.drop_index(op.f("ix_solves_created_at"), table_name="solves")
