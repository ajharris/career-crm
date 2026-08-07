"""Tests for the Milestone 1 application foundation."""

from sqlalchemy import inspect

from app import create_app
from app.extensions import db


def test_dashboard_renders_placeholder_statistics(authenticated_client) -> None:
    response = authenticated_client.get("/")

    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Organizations" in response.data
    assert response.data.count(b'display-6 mb-0">0') == 5


def test_not_found_uses_custom_error_page(authenticated_client) -> None:
    response = authenticated_client.get("/does-not-exist")

    assert response.status_code == 404
    assert b"The page you requested could not be found." in response.data


def test_init_db_command_creates_user_table() -> None:
    app = create_app("testing")

    result = app.test_cli_runner().invoke(args=["init-db"])

    assert result.exit_code == 0
    with app.app_context():
        assert "users" in inspect(db.engine).get_table_names()
