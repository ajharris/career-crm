"""Central ownership and shared-record authorization helpers."""

from types import SimpleNamespace
from typing import Any, cast

from flask import abort, has_request_context
from flask_login import current_user
from sqlalchemy import text

from app.extensions import db


def actor_id() -> int:
    """Return the authenticated user's ID for application-controlled fields."""
    if has_request_context() and current_user.is_authenticated:
        return int(current_user.id)
    actor = _single_user_outside_request()
    if actor is None:
        raise RuntimeError("An authenticated user is required.")
    return actor.id


def private_scope(model: type, user: Any = None):
    """Return a SQL ownership predicate, with the documented admin override."""
    user = user or _actor()
    if not user.is_authenticated:
        raise RuntimeError("An authenticated user is required.")
    scoped_model = cast(Any, model)
    return True if user.is_admin else scoped_model.owner_id == user.id


def can_view_private_record(record: Any, user: Any = None) -> bool:
    """Return whether a user may access a private record."""
    user = user or _actor()
    return bool(user.is_authenticated and (user.is_admin or record.owner_id == user.id))


def require_private_record(record: Any, user: Any = None) -> None:
    """Hide another user's private record behind a 404 response."""
    if not can_view_private_record(record, user):
        abort(404)


def can_edit_shared(record: Any, user: Any = None) -> bool:
    """Return whether a user may mutate a shared record."""
    user = user or _actor()
    return bool(
        user.is_authenticated and (user.is_admin or record.created_by_id == user.id)
    )


def require_shared_editor(record: Any, user: Any = None) -> None:
    """Reject non-creators attempting to mutate a shared record."""
    if not can_edit_shared(record, user):
        abort(403)


def _actor() -> Any:
    if has_request_context():
        return current_user
    return _single_user_outside_request() or SimpleNamespace(
        is_authenticated=False, is_admin=False, id=None
    )


def _single_user_outside_request() -> Any | None:
    """Support trusted single-user CLI/service calls without weakening HTTP auth."""
    rows = db.session.execute(
        text("SELECT id, is_admin FROM users ORDER BY id LIMIT 2")
    ).all()
    if len(rows) != 1:
        return None
    return SimpleNamespace(
        id=rows[0].id,
        is_admin=bool(rows[0].is_admin),
        is_authenticated=True,
    )
