"""github_integration and github_submission_syncs

Revision ID: 0019_github_integration
Revises: 0018_user_writeups_and_follows
Create Date: 2026-09-19 04:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0019_github_integration'
down_revision = '0018_user_writeups_and_follows'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    # 1. Add github fields to users if missing
    user_columns = [col['name'] for col in insp.get_columns('users')]
    if 'github_profile_url' not in user_columns:
        op.add_column('users', sa.Column('github_profile_url', sa.String(length=255), nullable=True))
    if 'github_username' not in user_columns:
        op.add_column('users', sa.Column('github_username', sa.String(length=100), nullable=True))

    # 2. github_integrations table
    if 'github_integrations' not in tables:
        op.create_table(
            'github_integrations',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('github_user_id', sa.String(length=100), nullable=True),
            sa.Column('github_username', sa.String(length=100), nullable=False),
            sa.Column('github_profile_url', sa.String(length=255), nullable=True),
            sa.Column('encrypted_access_token', sa.Text(), nullable=False),
            sa.Column('token_type', sa.String(length=50), server_default='bearer', nullable=False),
            sa.Column('scope', sa.String(length=255), server_default='repo,read:user', nullable=False),
            sa.Column('selected_repository', sa.String(length=255), nullable=True),
            sa.Column('repository_url', sa.String(length=512), nullable=True),
            sa.Column('is_connected', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_sync_status', sa.String(length=50), nullable=True),
            sa.Column('last_sync_error', sa.Text(), nullable=True),
            sa.Column('last_commit_sha', sa.String(length=100), nullable=True),
            sa.Column('last_commit_url', sa.String(length=512), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', name='uq_github_integrations_user_id')
        )
        op.create_index('ix_github_integrations_id', 'github_integrations', ['id'], unique=False)
        op.create_index('ix_github_integrations_user_id', 'github_integrations', ['user_id'], unique=True)
        op.create_index('ix_github_integrations_github_username', 'github_integrations', ['github_username'], unique=False)
        op.create_index('ix_github_integrations_is_connected', 'github_integrations', ['is_connected'], unique=False)

    # 3. github_submission_syncs table
    if 'github_submission_syncs' not in tables:
        op.create_table(
            'github_submission_syncs',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('challenge_id', sa.Uuid(), nullable=False),
            sa.Column('submission_id', sa.Uuid(), nullable=True),
            sa.Column('solve_id', sa.Uuid(), nullable=True),
            sa.Column('file_path', sa.String(length=255), nullable=False),
            sa.Column('commit_sha', sa.String(length=100), nullable=True),
            sa.Column('commit_url', sa.String(length=512), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='synced', nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['solve_id'], ['solves.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'challenge_id', name='uq_github_user_challenge_sync')
        )
        op.create_index('ix_github_submission_syncs_id', 'github_submission_syncs', ['id'], unique=False)
        op.create_index('ix_github_submission_syncs_user_id', 'github_submission_syncs', ['user_id'], unique=False)
        op.create_index('ix_github_submission_syncs_challenge_id', 'github_submission_syncs', ['challenge_id'], unique=False)


def downgrade() -> None:
    op.drop_table('github_submission_syncs')
    op.drop_table('github_integrations')
    conn = op.get_bind()
    insp = sa.inspect(conn)
    user_columns = [col['name'] for col in insp.get_columns('users')]
    if 'github_username' in user_columns:
        op.drop_column('users', 'github_username')
    if 'github_profile_url' in user_columns:
        op.drop_column('users', 'github_profile_url')
