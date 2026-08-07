"""User model, authentication flow, and account management tests."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.auth.services import create_user
from app.extensions import db


PASSWORD = "correct horse battery staple"


def registration_data(**extra):
    data = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ADA@Example.COM ",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    data.update(extra)
    return data


def test_user_model_hashing_normalization_and_defaults(app):
    user = create_user(
        first_name=" Ada ",
        last_name=" Lovelace ",
        email=" ADA@Example.COM ",
        password=PASSWORD,
    )
    assert user.email == "ada@example.com"
    assert user.full_name == "Ada Lovelace"
    assert user.password_hash != PASSWORD
    assert user.check_password(PASSWORD) and not user.check_password("wrong")
    assert user.is_active and not user.is_admin and not user.email_verified
    assert user.created_at and user.updated_at and user.last_login_at is None


def test_user_email_is_unique(app):
    create_user(
        first_name="First",
        last_name="User",
        email="same@example.com",
        password=PASSWORD,
    )
    duplicate = User(
        first_name="Other",
        last_name="User",
        email="SAME@example.com",
        password_hash="not-used",
    )
    db.session.add(duplicate)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_registration_page_and_success(client):
    assert client.get("/auth/register").status_code == 200
    response = client.post("/auth/register", data=registration_data())
    assert response.status_code == 302 and response.location == "/"
    assert client.get("/auth/profile").status_code == 200
    registered = db.session.scalar(
        db.select(User).where(User.email == "ada@example.com")
    )
    assert registered is not None


def test_registration_validation(client, user):
    duplicate = client.post(
        "/auth/register", data=registration_data(email=user.email)
    )
    mismatch = client.post(
        "/auth/register", data=registration_data(confirm_password="different")
    )
    assert b"already registered" in duplicate.data
    assert b"Passwords must match" in mismatch.data


def test_login_success_remember_last_login_and_safe_next(client, user):
    response = client.post(
        "/auth/login?next=/organizations",
        data={"email": " TEST@EXAMPLE.COM ", "password": PASSWORD, "remember": "y"},
    )
    assert response.location == "/organizations"
    assert "remember_token=" in response.headers.get("Set-Cookie", "")
    assert isinstance(db.session.get(User, user.id).last_login_at, datetime)


def test_login_rejects_invalid_credentials_and_external_next(client, user):
    invalid = client.post(
        "/auth/login", data={"email": user.email, "password": "incorrect"}
    )
    assert b"Invalid email or password" in invalid.data
    response = client.post(
        "/auth/login?next=https://attacker.example/steal",
        data={"email": user.email, "password": PASSWORD},
    )
    assert response.location == "/"


def test_logout_is_post_only_and_ends_session(authenticated_client):
    assert authenticated_client.get("/auth/logout").status_code == 405
    response = authenticated_client.post("/auth/logout", follow_redirects=True)
    assert b"You have been logged out" in response.data
    assert authenticated_client.get("/").status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/organizations",
        "/contacts",
        "/jobs",
        "/applications",
        "/activities",
        "/tasks",
    ],
)
def test_crm_routes_require_authentication(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location.startswith("/auth/login?next=")


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/organizations",
        "/contacts",
        "/jobs",
        "/applications",
        "/activities",
        "/tasks",
    ],
)
def test_authenticated_user_can_access_crm(authenticated_client, path):
    assert authenticated_client.get(path).status_code == 200


def test_profile_and_edit_reset_verification(authenticated_client, user):
    user.email_verified = True
    db.session.commit()
    assert b"Test User" in authenticated_client.get("/auth/profile").data
    response = authenticated_client.post(
        "/auth/profile/edit",
        data={"first_name": "Updated", "last_name": "Name", "email": "NEW@EXAMPLE.COM"},
        follow_redirects=True,
    )
    assert b"Your profile has been updated" in response.data
    db.session.refresh(user)
    assert user.full_name == "Updated Name"
    assert user.email == "new@example.com" and not user.email_verified


def test_profile_rejects_duplicate_email(authenticated_client, user):
    create_user(
        first_name="Another",
        last_name="User",
        email="another@example.com",
        password=PASSWORD,
    )
    response = authenticated_client.post(
        "/auth/profile/edit",
        data={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": "ANOTHER@example.com",
        },
    )
    assert b"already registered" in response.data


def test_change_password_verifies_current_secret(authenticated_client, user):
    wrong = authenticated_client.post(
        "/auth/password/change",
        data={
            "current_password": "wrong",
            "new_password": "a newer secure password",
            "confirm_password": "a newer secure password",
        },
    )
    assert b"Current password is incorrect" in wrong.data
    response = authenticated_client.post(
        "/auth/password/change",
        data={
            "current_password": PASSWORD,
            "new_password": "a newer secure password",
            "confirm_password": "a newer secure password",
        },
        follow_redirects=True,
    )
    assert b"Your password has been updated" in response.data
    db.session.refresh(user)
    assert user.check_password("a newer secure password")
    assert not user.check_password(PASSWORD)
