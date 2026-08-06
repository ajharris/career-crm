"""Business operations for organizations."""

from typing import TypedDict, Unpack

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, or_, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.organization import Organization


class DuplicateOrganizationError(ValueError):
    """Raised when an organization name is already in use."""


class OrganizationValues(TypedDict, total=False):
    """Values accepted when creating or updating an organization."""

    name: str
    organization_type: str | None
    website: str | None
    location: str | None
    priority: int
    notes: str | None


SORT_COLUMNS = {
    "name": Organization.name,
    "priority": Organization.priority,
    "created_at": Organization.created_at,
}


def list_organizations(
    *, search: str = "", sort: str = "name", direction: str = "asc", page: int = 1
) -> Pagination:
    """Return a searched, sorted page of organizations."""
    statement = select(Organization)
    if search := search.strip():
        pattern = f"%{_escape_like(search)}%"
        type_pattern = f"%{_escape_like(search.replace(' ', '_'))}%"
        statement = statement.where(
            or_(
                Organization.name.ilike(pattern, escape="\\"),
                Organization.organization_type.ilike(type_pattern, escape="\\"),
                Organization.location.ilike(pattern, escape="\\"),
            )
        )
    statement = _apply_sort(statement, sort, direction)
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def get_organization(organization_id: int) -> Organization:
    """Return one organization or raise a 404 response."""
    return db.get_or_404(Organization, organization_id)


def create_organization(**values: Unpack[OrganizationValues]) -> Organization:
    """Create and persist an organization."""
    organization = Organization()
    _apply_values(organization, values)
    db.session.add(organization)
    _commit(organization.name)
    return organization


def update_organization(
    organization: Organization, **values: Unpack[OrganizationValues]
) -> Organization:
    """Update and persist an organization."""
    _apply_values(organization, values)
    _commit(organization.name)
    return organization


def delete_organization(organization: Organization) -> None:
    """Delete an organization."""
    db.session.delete(organization)
    db.session.commit()


def _apply_values(
    organization: Organization, values: OrganizationValues
) -> None:
    allowed = {
        "name",
        "organization_type",
        "website",
        "location",
        "priority",
        "notes",
    }
    for field in allowed:
        if field in values:
            value = values[field]
            if field != "name" and isinstance(value, str):
                value = value.strip() or None
            setattr(organization, field, value)


def _commit(name: str) -> None:
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateOrganizationError(
            f'An organization named "{name}" already exists.'
        ) from exc


def _apply_sort(
    statement: Select[tuple[Organization]], sort: str, direction: str
) -> Select[tuple[Organization]]:
    column = SORT_COLUMNS.get(sort, Organization.name)
    order = desc if direction == "desc" else asc
    return statement.order_by(order(column), asc(Organization.id))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
