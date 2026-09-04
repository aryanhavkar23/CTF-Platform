"""challenge management additions

Revision ID: 0002_challenge_mgmt
Revises: 0001_initial
Create Date: 2026-09-05 02:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_challenge_mgmt"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to challenges table
    with op.batch_alter_table("challenges") as batch_op:
        batch_op.add_column(sa.Column("is_live_instance", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("docker_image", sa.String(length=255), nullable=True))

    # 2. Create challenge_files table
    op.create_table(
        "challenge_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_challenge_files_id"), "challenge_files", ["id"], unique=False)
    op.create_index(op.f("ix_challenge_files_challenge_id"), "challenge_files", ["challenge_id"], unique=False)

    # 3. Create challenge_hints table
    op.create_table(
        "challenge_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("point_deduction", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("point_deduction >= 0", name="check_positive_hint_deduction"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_challenge_hints_id"), "challenge_hints", ["id"], unique=False)
    op.create_index(op.f("ix_challenge_hints_challenge_id"), "challenge_hints", ["challenge_id"], unique=False)

    # 4. Create challenge_writeups table
    op.create_table(
        "challenge_writeups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "visibility",
            sa.Enum("hidden", "after_solve", "after_event", "public", name="writeupvisibility", native_enum=False, length=20),
            nullable=False,
            server_default="hidden"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", name="uq_challenge_writeups_challenge_id"),
    )
    op.create_index(op.f("ix_challenge_writeups_id"), "challenge_writeups", ["id"], unique=False)
    op.create_index(op.f("ix_challenge_writeups_challenge_id"), "challenge_writeups", ["challenge_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_challenge_writeups_challenge_id"), table_name="challenge_writeups")
    op.drop_index(op.f("ix_challenge_writeups_id"), table_name="challenge_writeups")
    op.drop_table("challenge_writeups")

    op.drop_index(op.f("ix_challenge_hints_challenge_id"), table_name="challenge_hints")
    op.drop_index(op.f("ix_challenge_hints_id"), table_name="challenge_hints")
    op.drop_table("challenge_hints")

    op.drop_index(op.f("ix_challenge_files_challenge_id"), table_name="challenge_files")
    op.drop_index(op.f("ix_challenge_files_id"), table_name="challenge_files")
    op.drop_table("challenge_files")

    with op.batch_alter_table("challenges") as batch_op:
        batch_op.drop_column("docker_image")
        batch_op.drop_column("is_live_instance")
