"""add is_dynamic_flag to challenges

Revision ID: 0020_add_is_dynamic_flag
Revises: 0019_github_integration
Create Date: 2026-09-19 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0020_add_is_dynamic_flag'
down_revision = '0019_github_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('challenges')]
    if 'is_dynamic_flag' not in cols:
        op.add_column(
            'challenges',
            sa.Column('is_dynamic_flag', sa.Boolean(), nullable=False, server_default=sa.text('false'))
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('challenges')]
    if 'is_dynamic_flag' in cols:
        op.drop_column('challenges', 'is_dynamic_flag')
