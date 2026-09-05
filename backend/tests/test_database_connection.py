import pytest
from sqlalchemy import text
from app.config import settings
from app.database import get_engine, SessionLocal, Base


def test_engine_initialization():
    """Verify that the engine initializes and can execute a test query."""
    test_engine = get_engine("sqlite:///:memory:")
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_metadata_tables_registered():
    """Verify that all required tables are registered with SQLAlchemy Base.metadata."""
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
    }
    registered_tables = set(Base.metadata.tables.keys())
    for table in expected_tables:
        assert table in registered_tables, f"Table {table} not registered in Base.metadata"


def test_settings_loaded():
    """Verify environment configuration settings load expected defaults."""
    assert settings.ENVIRONMENT in ["development", "testing", "production"]
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
