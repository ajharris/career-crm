"""Business operations and queries for contacts."""

from datetime import datetime
from typing import TypedDict, Unpack

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, func, or_, select

from app.auth.permissions import actor_id, private_scope, require_private_record
from app.extensions import db
from app.models.contact import Contact
from app.models.organization import Organization


class ContactValues(TypedDict, total=False):
    """Values accepted when creating or updating a contact."""

    organization_id: int
    first_name: str
    last_name: str
    title: str | None
    department: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    profile_url: str | None
    resume_url: str | None
    notes: str | None
    relationship_status: str | None
    last_contacted_at: datetime | None


SORT_COLUMNS = {
    "last_name": Contact.last_name,
    "organization": Organization.name,
    "created_at": Contact.created_at,
    "last_contacted_at": Contact.last_contacted_at,
}


def list_contacts(
    *,
    search: str = "",
    organization_id: int | None = None,
    title: str = "",
    sort: str = "last_name",
    direction: str = "asc",
    page: int = 1,
) -> Pagination:
    """Return a filtered and searched page of contacts."""
    statement = select(Contact).join(Contact.organization).where(private_scope(Contact))
    if search := search.strip():
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Organization.name.ilike(pattern, escape="\\"),
                Contact.title.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.profile_url.ilike(pattern, escape="\\"),
                Contact.resume_url.ilike(pattern, escape="\\"),
            )
        )
    if organization_id is not None:
        statement = statement.where(Contact.organization_id == organization_id)
    if title := title.strip():
        statement = statement.where(func.lower(Contact.title) == title.lower())
    statement = _apply_sort(statement, sort, direction)
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def get_contact(contact_id: int) -> Contact:
    """Return one contact or raise a 404 response."""
    return db.first_or_404(
        select(Contact).where(Contact.id == contact_id, private_scope(Contact))
    )


def create_contact(**values: Unpack[ContactValues]) -> Contact:
    """Create and persist a contact belonging to an organization."""
    contact = Contact()
    contact.owner_id = actor_id()
    _apply_values(contact, values)
    _require_organization(contact.organization_id)
    db.session.add(contact)
    db.session.commit()
    return contact


def update_contact(contact: Contact, **values: Unpack[ContactValues]) -> Contact:
    """Update and persist a contact."""
    require_private_record(contact)
    _apply_values(contact, values)
    _require_organization(contact.organization_id)
    db.session.commit()
    return contact


def delete_contact(contact: Contact) -> None:
    """Delete a contact."""
    require_private_record(contact)
    db.session.delete(contact)
    db.session.commit()


def organization_choices() -> list[tuple[int, str]]:
    """Return organizations ordered for form and filter controls."""
    organizations = db.session.scalars(
        select(Organization).order_by(Organization.name)
    ).all()
    return [(organization.id, organization.name) for organization in organizations]


def title_choices() -> list[str]:
    """Return distinct non-empty contact titles for filtering."""
    titles = db.session.scalars(
        select(Contact.title)
        .where(private_scope(Contact), Contact.title.is_not(None), Contact.title != "")
        .distinct()
        .order_by(Contact.title)
    ).all()
    return [title for title in titles if title is not None]


def contacts_for_organization(organization_id: int) -> list[Contact]:
    """Return the current user's contacts for a shared organization."""
    return list(
        db.session.scalars(
            select(Contact)
            .where(Contact.organization_id == organization_id, private_scope(Contact))
            .order_by(Contact.last_name, Contact.first_name)
        )
    )


def _apply_values(contact: Contact, values: ContactValues) -> None:
    allowed = {
        "organization_id",
        "first_name",
        "last_name",
        "title",
        "department",
        "email",
        "phone",
        "linkedin_url",
        "profile_url",
        "resume_url",
        "notes",
        "relationship_status",
        "last_contacted_at",
    }
    for field in allowed:
        if field in values:
            value = values[field]
            if field not in {"first_name", "last_name"} and isinstance(value, str):
                value = value.strip() or None
            setattr(contact, field, value)


def _require_organization(organization_id: int) -> None:
    if db.session.get(Organization, organization_id) is None:
        raise ValueError("A valid organization is required.")


def _apply_sort(
    statement: Select[tuple[Contact]], sort: str, direction: str
) -> Select[tuple[Contact]]:
    """Apply an allow-listed stable sort to a contact query."""
    column = SORT_COLUMNS.get(sort, Contact.last_name)
    order = desc if direction == "desc" else asc
    primary_order = order(column)
    if sort == "last_contacted_at":
        primary_order = primary_order.nulls_last()
    return statement.order_by(primary_order, asc(Contact.last_name), asc(Contact.id))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
