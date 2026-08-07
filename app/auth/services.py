"""Authentication and account business operations."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.extensions import db


class EmailAlreadyRegisteredError(ValueError):
    """Raised when an account email conflicts with another user."""


class InvalidCurrentPasswordError(ValueError):
    """Raised when a password change cannot be authorized."""


def normalize_email(email: str) -> str:
    """Return the canonical account lookup form of an email address."""
    return email.strip().lower()


def create_user(*, first_name: str, last_name: str, email: str, password: str) -> User:
    """Create an account with a secure password hash."""
    normalized = normalize_email(email)
    if find_user_by_email(normalized):
        raise EmailAlreadyRegisteredError("That email address is already registered.")
    user = User(first_name=first_name, last_name=last_name, email=normalized)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    from app.models.career_profile import CareerProfile

    db.session.add(CareerProfile(user_id=user.id))
    _commit_unique()
    return user


def authenticate_user(email: str, password: str) -> User | None:
    """Validate credentials without disclosing which component failed."""
    user = find_user_by_email(email)
    if user is None or not user.is_active or not user.check_password(password):
        return None
    user.last_login_at = datetime.now(UTC)
    db.session.commit()
    return user


def update_profile(
    user: User, *, first_name: str, last_name: str, email: str
) -> User:
    """Update editable profile fields and invalidate a changed email."""
    normalized = normalize_email(email)
    existing = find_user_by_email(normalized)
    if existing is not None and existing.id != user.id:
        raise EmailAlreadyRegisteredError("That email address is already registered.")
    if user.email != normalized:
        user.email = normalized
        user.email_verified = False
    user.first_name = first_name
    user.last_name = last_name
    _commit_unique()
    return user


def change_password(user: User, current_password: str, new_password: str) -> None:
    """Replace a password only after verifying the current secret."""
    if not user.check_password(current_password):
        raise InvalidCurrentPasswordError("Current password is incorrect.")
    user.set_password(new_password)
    db.session.commit()


def find_user_by_email(email: str) -> User | None:
    return db.session.scalar(
        select(User).where(func.lower(User.email) == normalize_email(email))
    )


def _commit_unique() -> None:
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise EmailAlreadyRegisteredError(
            "That email address is already registered."
        ) from exc
