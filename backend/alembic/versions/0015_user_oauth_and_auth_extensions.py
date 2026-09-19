"""user oauth and auth extensions Phase 18 schema

Revision ID: 0015_user_oauth_and_auth_extensions
Revises: 0014_user_moderation_fields
Create Date: 2026-09-15 08:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0015_user_oauth_and_auth_extensions"
down_revision: Union[str, None] = "0014_user_moderation_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("oauth_provider", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("oauth_id", sa.String(length=255), nullable=True))
        batch_op.create_index("ix_users_oauth_id", ["oauth_id"])
        batch_op.alter_column("hashed_password", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_oauth_id")
        batch_op.drop_column("oauth_id")
        batch_op.drop_column("oauth_provider")
        batch_op.alter_column("hashed_password", existing_type=sa.String(length=255), nullable=False)
