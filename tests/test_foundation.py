"""Tests for the Milestone 1 application foundation."""

from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.utils.text import linkify_text


def test_linkify_text_safely_links_urls_and_email_addresses() -> None:
    rendered = str(
        linkify_text(
            "Visit https://example.com/path?x=1&y=2 or email person@example.com. "
            "<script>alert('x')</script>"
        )
    )

    assert (
        'href="https://example.com/path?x=1&amp;y=2" rel="noopener noreferrer"'
        in rendered
    )
    assert 'href="mailto:person@example.com"' in rendered
    assert "person@example.com</a>." in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


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
