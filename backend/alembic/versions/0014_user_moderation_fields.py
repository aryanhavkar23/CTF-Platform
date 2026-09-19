"""user moderation fields Phase 17 schema

Revision ID: 0014_user_moderation_fields
Revises: 0013_live_challenge_instances
Create Date: 2026-09-14 09:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0014_user_moderation_fields"
down_revision: Union[str, None] = "0013_live_challenge_instances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_muted")
        batch_op.drop_column("is_banned")
