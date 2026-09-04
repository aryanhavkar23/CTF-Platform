import sys
from sqlalchemy import inspect
from app.database import engine, Base
import app.models  # Ensure all models are loaded


def init_database() -> None:
    """Creates tables directly using SQLAlchemy metadata."""
    print("Creating all tables in database...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")


def verify_tables() -> dict:
    """Inspects the database schema and returns created tables and columns."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    schema_info = {}
    for table_name in tables:
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        foreign_keys = [
            f"{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
            for fk in inspector.get_foreign_keys(table_name)
        ]
        schema_info[table_name] = {
            "columns": columns,
            "foreign_keys": foreign_keys,
        }
    return schema_info


if __name__ == "__main__":
    try:
        init_database()
        info = verify_tables()
        print("\nVerified Tables:")
        for table, details in info.items():
            print(f"  - {table} ({len(details['columns'])} columns)")
            for fk in details["foreign_keys"]:
                print(f"      FK: {fk}")
    except Exception as e:
        print(f"Database initialization error: {e}", file=sys.stderr)
        sys.exit(1)
