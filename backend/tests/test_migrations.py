import os
from pathlib import Path
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_and_downgrade(tmp_path):
    """Test applying and reverting Alembic migrations against a test database."""
    test_db_file = tmp_path / "migration_test.db"
    test_db_url = f"sqlite:///{test_db_file}"

    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    # Set up Alembic config and environment
    os.environ["DATABASE_URL"] = test_db_url
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("version_locations", str(backend_dir / "alembic" / "versions"))

    # 1. Test upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify tables were created by migration
    engine = create_engine(test_db_url)
    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())

    expected_tables = {
        "users",
        "teams",
        "team_members",
        "categories",
        "challenges",
        "events",
        "event_challenges",
        "submissions",
        "challenge_files",
        "challenge_hints",
        "challenge_writeups",
        "solves",
        "hint_usage",
        "event_registrations",
        "user_activities",
        "badges",
        "user_badges",
        "discussions",
        "discussion_comments",
        "notifications",
        "security_events",
        "security_event_reviews",
        "user_writeups",
        "user_follows",
        "github_submission_syncs",
    }
    for table in expected_tables:
        assert table in created_tables, f"Table {table} was not created by migration"

    solves_indexes = {ix["name"] for ix in inspector.get_indexes("solves")}
    assert "ix_solves_created_at" in solves_indexes

    users_indexes = {ix["name"] for ix in inspector.get_indexes("users")}
    assert "ix_users_college" in users_indexes
    assert "ix_users_oauth_id" in users_indexes

    activity_indexes = {ix["name"] for ix in inspector.get_indexes("user_activities")}
    assert "ix_user_activities_created_at" in activity_indexes

    badge_indexes = {ix["name"] for ix in inspector.get_indexes("badges")}
    assert "ix_badges_slug" in badge_indexes

    user_badge_indexes = {ix["name"] for ix in inspector.get_indexes("user_badges")}
    assert "ix_user_badges_user_id" in user_badge_indexes

    # 2. Test downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Verify tables were dropped
    inspector = inspect(engine)
    remaining_tables = set(inspector.get_table_names())
    for table in expected_tables:
        assert table not in remaining_tables, f"Table {table} remained after downgrade"
