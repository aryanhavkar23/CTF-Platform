"""discussions and comments Phase 11 schema

Revision ID: 0010_discussions_and_comments
Revises: 0009_badges_and_achievements
Create Date: 2026-09-07 08:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010_discussions_and_comments"
down_revision: Union[str, None] = "0009_badges_and_achievements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create discussions table
    op.create_table(
        "discussions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("challenge_id", sa.Uuid(), sa.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contains_spoiler", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_discussions_id", "discussions", ["id"])
    op.create_index("ix_discussions_challenge_id", "discussions", ["challenge_id"])
    op.create_index("ix_discussions_user_id", "discussions", ["user_id"])
    op.create_index("ix_discussions_is_pinned", "discussions", ["is_pinned"])
    op.create_index("ix_discussions_created_at", "discussions", ["created_at"])

    # 2. Create discussion_comments table
    op.create_table(
        "discussion_comments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("discussion_id", sa.Uuid(), sa.ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_comment_id", sa.Uuid(), sa.ForeignKey("discussion_comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contains_spoiler", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_discussion_comments_id", "discussion_comments", ["id"])
    op.create_index("ix_discussion_comments_discussion_id", "discussion_comments", ["discussion_id"])
    op.create_index("ix_discussion_comments_user_id", "discussion_comments", ["user_id"])
    op.create_index("ix_discussion_comments_parent_comment_id", "discussion_comments", ["parent_comment_id"])
    op.create_index("ix_discussion_comments_created_at", "discussion_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_discussion_comments_created_at", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_parent_comment_id", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_user_id", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_discussion_id", table_name="discussion_comments")
    op.drop_index("ix_discussion_comments_id", table_name="discussion_comments")
    op.drop_table("discussion_comments")

    op.drop_index("ix_discussions_created_at", table_name="discussions")
    op.drop_index("ix_discussions_is_pinned", table_name="discussions")
    op.drop_index("ix_discussions_user_id", table_name="discussions")
    op.drop_index("ix_discussions_challenge_id", table_name="discussions")
    op.drop_index("ix_discussions_id", table_name="discussions")
    op.drop_table("discussions")
