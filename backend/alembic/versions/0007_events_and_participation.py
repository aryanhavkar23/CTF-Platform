"""events and event participation Phase 8 schema

Revision ID: 0007_events_and_participation
Revises: 0006_teams_and_members
Create Date: 2026-09-05 12:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_events_and_participation"
down_revision: Union[str, None] = "0006_teams_and_members"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update events table
    op.add_column("events", sa.Column("slug", sa.String(length=150), nullable=True))
    op.add_column("events", sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("registration_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("registration_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("status", sa.String(length=20), server_default="upcoming", nullable=False))
    op.add_column("events", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("events", sa.Column("scoreboard_frozen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("created_by", sa.Uuid(), nullable=True))

    # Backfill slug, start_at, end_at
    op.execute("UPDATE events SET slug = LOWER(REPLACE(name, ' ', '-')) WHERE slug IS NULL")
    op.execute("UPDATE events SET start_at = start_time WHERE start_at IS NULL")
    op.execute("UPDATE events SET end_at = end_time WHERE end_at IS NULL")

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column("slug", nullable=False)
        batch_op.alter_column("start_at", nullable=False)
        batch_op.alter_column("end_at", nullable=False)
        batch_op.create_index(batch_op.f("ix_events_slug"), ["slug"], unique=True)
        batch_op.create_index(batch_op.f("ix_events_start_at"), ["start_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_end_at"), ["end_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_created_by"), ["created_by"], unique=False)
        batch_op.create_foreign_key("fk_events_created_by_users", "users", ["created_by"], ["id"], ondelete="SET NULL")

    # 2. Update event_challenges table
    op.add_column("event_challenges", sa.Column("display_order", sa.Integer(), server_default="1", nullable=False))
    op.add_column("event_challenges", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    # 3. Update solves table
    op.add_column("solves", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.add_column("solves", sa.Column("team_id", sa.Uuid(), nullable=True))
    with op.batch_alter_table("solves", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_solves_event_id"), ["event_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_solves_team_id"), ["team_id"], unique=False)
        batch_op.create_foreign_key("fk_solves_event_id_events", "events", ["event_id"], ["id"], ondelete="CASCADE")
        batch_op.create_foreign_key("fk_solves_team_id_teams", "teams", ["team_id"], ["id"], ondelete="CASCADE")
        try:
            batch_op.drop_constraint("uq_user_challenge_solve", type_="unique")
        except Exception:
            pass

    # 4. Create event_registrations table
    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("registration_type", sa.String(length=20), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(registration_type = 'individual' AND user_id IS NOT NULL AND team_id IS NULL) OR "
            "(registration_type = 'team' AND team_id IS NOT NULL AND user_id IS NULL)",
            name="chk_event_reg_participant_type"
        ),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_user_reg"),
        sa.UniqueConstraint("event_id", "team_id", name="uq_event_team_reg")
    )
    op.create_index(op.f("ix_event_registrations_id"), "event_registrations", ["id"], unique=False)
    op.create_index(op.f("ix_event_registrations_event_id"), "event_registrations", ["event_id"], unique=False)
    op.create_index(op.f("ix_event_registrations_user_id"), "event_registrations", ["user_id"], unique=False)
    op.create_index(op.f("ix_event_registrations_team_id"), "event_registrations", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_table("event_registrations")

    with op.batch_alter_table("solves", schema=None) as batch_op:
        batch_op.drop_constraint("fk_solves_team_id_teams", type_="foreignkey")
        batch_op.drop_constraint("fk_solves_event_id_events", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_solves_team_id"))
        batch_op.drop_index(batch_op.f("ix_solves_event_id"))
        batch_op.drop_column("team_id")
        batch_op.drop_column("event_id")

    with op.batch_alter_table("event_challenges", schema=None) as batch_op:
        batch_op.drop_column("is_active")
        batch_op.drop_column("display_order")

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_constraint("fk_events_created_by_users", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_events_created_by"))
        batch_op.drop_index(batch_op.f("ix_events_status"))
        batch_op.drop_index(batch_op.f("ix_events_end_at"))
        batch_op.drop_index(batch_op.f("ix_events_start_at"))
        batch_op.drop_index(batch_op.f("ix_events_slug"))
        batch_op.drop_column("created_by")
        batch_op.drop_column("scoreboard_frozen_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("status")
        batch_op.drop_column("registration_end_at")
        batch_op.drop_column("registration_start_at")
        batch_op.drop_column("end_at")
        batch_op.drop_column("start_at")
        batch_op.drop_column("slug")
