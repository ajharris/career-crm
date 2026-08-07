"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.auth.models import User
from app.auth.services import create_user
from app.extensions import db


@pytest.fixture
def app() -> Iterator[Flask]:
    """Create an isolated application and database for each test."""
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Return an anonymous test HTTP client."""
    return app.test_client()


@pytest.fixture
def user(app: Flask) -> User:
    """Create a reusable account for authenticated tests."""
    return create_user(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password="correct horse battery staple",
    )


@pytest.fixture
def authenticated_client(app: Flask, user: User) -> FlaskClient:
    """Return a client logged in through the public authentication flow."""
    test_client = app.test_client()
    response = test_client.post(
        "/auth/login",
        data={"email": user.email, "password": "correct horse battery staple"},
    )
    assert response.status_code == 302
    return test_client
