"""Alembic migration-chain smoke tests against isolated SQLite databases."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LATE_TABLES = {
    "job_skills",
    "documents",
    "document_versions",
    "application_documents",
    "saved_searches",
    "notification_dismissals",
    "organization_notes",
    "company_reviews",
    "user_ai_provider_credentials",
    "instance_storage_configuration",
}


def _upgrade(database: Path, revision: str = "head"):
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database}",
            "APP_ENV": "development",
            "FLASK_APP": "wsgi:app",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade", revision],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def test_empty_database_upgrades_to_single_head_with_expected_tables(tmp_path):
    database = tmp_path / "fresh.db"
    result = _upgrade(database)
    assert result.returncode == 0, result.stderr
    inspector = inspect(create_engine(f"sqlite:///{database}"))
    tables = set(inspector.get_table_names())
    assert EXPECTED_LATE_TABLES.issubset(tables)
    contact_columns = {
        column["name"] for column in inspector.get_columns("contacts")
    }
    assert {"profile_url", "resume_url"}.issubset(contact_columns)
    with sqlite3.connect(database) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert revision == "d64a13b5e8c2"


def test_upgrade_from_onboarding_revision_preserves_reference_data(tmp_path):
    database = tmp_path / "upgrade.db"
    initial = _upgrade(database, "e84c61bd20a7")
    assert initial.returncode == 0, initial.stderr
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO industries (name) VALUES (?)", ("Test Domain",))
        connection.commit()

    final = _upgrade(database)
    assert final.returncode == 0, final.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM industries WHERE name = ?", ("Test Domain",)
        ).fetchone() == ("Test Domain",)
