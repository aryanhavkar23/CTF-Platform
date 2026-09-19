"""ensure challenge_type column

Revision ID: 0017_ensure_challenge_type_column
Revises: 0016_remove_docker_add_external_url
Create Date: 2026-09-18 16:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0017_ensure_challenge_type_column'
down_revision = '0016_remove_docker_add_external_url'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure challenge_type column exists on challenges table
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('challenges')]
    if 'challenge_type' not in cols:
        op.add_column('challenges', sa.Column('challenge_type', sa.String(length=20), nullable=True, server_default='STATIC'))
        op.execute("UPDATE challenges SET challenge_type = 'STATIC' WHERE challenge_type IS NULL")


def downgrade() -> None:
    pass
