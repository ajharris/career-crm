"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.auth.models import User
from app.auth.services import create_user
from app.extensions import db
from app.models import Application, JobPosting, Organization, Skill
from app.models.career_profile import CareerProfile

PASSWORD = "correct horse battery staple"


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
        create_user(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="correct horse battery staple",
        )
        profile = db.session.scalar(db.select(CareerProfile))
        profile.onboarding_completed = True
        db.session.commit()
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
    """Return the default account used by authenticated tests."""
    return db.session.scalar(db.select(User).where(User.email == "test@example.com"))


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


def _create_completed_user(email: str, first_name: str, *, is_admin: bool = False):
    account = create_user(
        first_name=first_name,
        last_name="Tester",
        email=email,
        password=PASSWORD,
    )
    account.is_admin = is_admin
    profile = db.session.scalar(
        db.select(CareerProfile).where(CareerProfile.user_id == account.id)
    )
    profile.onboarding_completed = True
    db.session.commit()
    return account


def _logged_in_client(app: Flask, account: User) -> FlaskClient:
    test_client = app.test_client()
    response = test_client.post(
        "/auth/login", data={"email": account.email, "password": PASSWORD}
    )
    assert response.status_code == 302
    return test_client


@pytest.fixture
def second_user(app: Flask) -> User:
    """A completed non-admin account for isolation and IDOR tests."""
    return _create_completed_user("second@example.com", "Second")


@pytest.fixture
def admin_user(app: Flask) -> User:
    """A completed administrator account."""
    return _create_completed_user("admin@example.com", "Admin", is_admin=True)


@pytest.fixture
def second_authenticated_client(app: Flask, second_user: User) -> FlaskClient:
    return _logged_in_client(app, second_user)


@pytest.fixture
def admin_client(app: Flask, admin_user: User) -> FlaskClient:
    return _logged_in_client(app, admin_user)


@pytest.fixture
def organization(user: User) -> Organization:
    record = Organization(
        name="Fixture Organization", created_by_id=user.id, updated_by_id=user.id
    )
    db.session.add(record)
    db.session.commit()
    return record


@pytest.fixture
def job_posting(user: User, organization: Organization) -> JobPosting:
    record = JobPosting(
        title="Fixture Engineer",
        organization=organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.session.add(record)
    db.session.commit()
    return record


@pytest.fixture
def application(user: User, job_posting: JobPosting) -> Application:
    record = Application(owner_id=user.id, job_posting=job_posting)
    db.session.add(record)
    db.session.commit()
    return record


@pytest.fixture
def skills(user: User) -> list[Skill]:
    records = [
        Skill(
            name=name,
            category=category,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        for name, category in (("Python", "programming"), ("SQL", "database"))
    ]
    db.session.add_all(records)
    db.session.commit()
    return records
