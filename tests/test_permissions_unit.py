"""Exhaustive ownership-helper behavior at the security boundary."""

from types import SimpleNamespace

import pytest
from werkzeug.exceptions import Forbidden, NotFound

from app.auth.permissions import (
    actor_id,
    can_edit_shared,
    can_view_private_record,
    private_scope,
    require_private_record,
    require_shared_editor,
)
from app.models import Contact


def _principal(identifier, *, authenticated=True, admin=False):
    return SimpleNamespace(
        id=identifier, is_authenticated=authenticated, is_admin=admin
    )


def test_actor_id_and_private_scope_fail_closed_without_unambiguous_actor(
    app, second_user
):
    with pytest.raises(RuntimeError, match="authenticated user"):
        actor_id()
    with app.test_request_context(), pytest.raises(RuntimeError):
        private_scope(Contact)


def test_private_record_permission_owner_admin_anonymous_and_other():
    record = SimpleNamespace(owner_id=1)
    assert can_view_private_record(record, _principal(1)) is True
    assert can_view_private_record(record, _principal(2, admin=True)) is True
    assert can_view_private_record(record, _principal(2)) is False
    assert (
        can_view_private_record(record, _principal(None, authenticated=False)) is False
    )
    with pytest.raises(NotFound):
        require_private_record(record, _principal(2))
    require_private_record(record, _principal(1))


def test_shared_edit_permission_creator_admin_anonymous_and_other():
    record = SimpleNamespace(created_by_id=1)
    assert can_edit_shared(record, _principal(1)) is True
    assert can_edit_shared(record, _principal(2, admin=True)) is True
    assert can_edit_shared(record, _principal(2)) is False
    assert can_edit_shared(record, _principal(None, authenticated=False)) is False
    with pytest.raises(Forbidden):
        require_shared_editor(record, _principal(2))
    require_shared_editor(record, _principal(1))


def test_admin_private_scope_is_unrestricted():
    assert private_scope(Contact, _principal(99, admin=True)) is True
    predicate = private_scope(Contact, _principal(3))
    assert str(predicate).endswith("contacts.owner_id = :owner_id_1")
