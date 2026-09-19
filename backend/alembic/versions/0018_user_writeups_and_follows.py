"""user_writeups and user_follows

Revision ID: 0018_user_writeups_and_follows
Revises: 0017_ensure_challenge_type_column
Create Date: 2026-09-18 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0018_user_writeups_and_follows'
down_revision = '0017_ensure_challenge_type_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. user_writeups
    if 'user_writeups' not in tables:
        op.create_table(
            'user_writeups',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('challenge_id', sa.Uuid(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('tags', sa.String(length=255), nullable=True),
            sa.Column('upvotes_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_user_writeups_id', 'user_writeups', ['id'], unique=False)
        op.create_index('ix_user_writeups_challenge_id', 'user_writeups', ['challenge_id'], unique=False)
        op.create_index('ix_user_writeups_user_id', 'user_writeups', ['user_id'], unique=False)
        op.create_index('ix_user_writeups_is_published', 'user_writeups', ['is_published'], unique=False)

    # 2. writeup_upvotes
    if 'writeup_upvotes' not in tables:
        op.create_table(
            'writeup_upvotes',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('writeup_id', sa.Uuid(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['writeup_id'], ['user_writeups.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('writeup_id', 'user_id', name='uq_writeup_user_upvote')
        )
        op.create_index('ix_writeup_upvotes_id', 'writeup_upvotes', ['id'], unique=False)
        op.create_index('ix_writeup_upvotes_writeup_id', 'writeup_upvotes', ['writeup_id'], unique=False)
        op.create_index('ix_writeup_upvotes_user_id', 'writeup_upvotes', ['user_id'], unique=False)

    # 3. user_follows
    if 'user_follows' not in tables:
        op.create_table(
            'user_follows',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('follower_id', sa.Uuid(), nullable=False),
            sa.Column('following_id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['following_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('follower_id', 'following_id', name='uq_user_follows')
        )
        op.create_index('ix_user_follows_id', 'user_follows', ['id'], unique=False)
        op.create_index('ix_user_follows_follower_id', 'user_follows', ['follower_id'], unique=False)
        op.create_index('ix_user_follows_following_id', 'user_follows', ['following_id'], unique=False)


def downgrade() -> None:
    op.drop_table('user_follows')
    op.drop_table('writeup_upvotes')
    op.drop_table('user_writeups')
