"""Business operations and timeline queries for activities."""

from datetime import UTC, date, datetime, time
from typing import Any, TypedDict, Unpack, cast

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, inspect, or_, select

from app.auth.permissions import actor_id, private_scope, require_private_record
from app.extensions import db
from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.utils.enums import ActivityDirection, ActivityType, ApplicationStatus


class ActivityValues(TypedDict, total=False):
    """Values accepted when creating or updating an activity."""

    organization_id: int | None
    contact_id: int | None
    job_posting_id: int | None
    application_id: int | None
    activity_type: str
    occurred_at: datetime
    direction: str
    subject: str | None
    summary: str | None
    outcome: str | None
    follow_up_needed: bool
    notes: str | None


SORT_COLUMNS = {
    "occurred_at": Activity.occurred_at,
    "activity_type": Activity.activity_type,
    "organization": Organization.name,
    "contact": Contact.last_name,
    "created_at": Activity.created_at,
}

SUBMITTED_STATUSES = {
    status
    for status in ApplicationStatus
    if status not in {ApplicationStatus.PLANNED, ApplicationStatus.PREPARING}
}


def list_activities(
    *,
    search: str = "",
    activity_type: str = "",
    direction: str = "",
    organization_id: int | None = None,
    contact_id: int | None = None,
    job_posting_id: int | None = None,
    application_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = "occurred_at",
    sort_direction: str = "desc",
    page: int = 1,
) -> Pagination:
    """Return a searched, filtered, sorted page of activities."""
    statement = (
        select(Activity)
        .outerjoin(Activity.organization)
        .outerjoin(Activity.contact)
        .where(private_scope(Activity))
    )
    if search := search.strip():
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                Activity.subject.ilike(pattern, escape="\\"),
                Activity.summary.ilike(pattern, escape="\\"),
                Activity.outcome.ilike(pattern, escape="\\"),
                Activity.notes.ilike(pattern, escape="\\"),
                Organization.name.ilike(pattern, escape="\\"),
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
            )
        )
    filters = {
        Activity.activity_type: activity_type,
        Activity.direction: direction,
        Activity.organization_id: organization_id,
        Activity.contact_id: contact_id,
        Activity.job_posting_id: job_posting_id,
        Activity.application_id: application_id,
    }
    for column, value in filters.items():
        if value not in {None, ""}:
            statement = statement.where(column == value)
    if date_from is not None:
        statement = statement.where(
            Activity.occurred_at >= datetime.combine(date_from, time.min)
        )
    if date_to is not None:
        statement = statement.where(
            Activity.occurred_at <= datetime.combine(date_to, time.max)
        )
    statement = _apply_sort(statement, sort, sort_direction)
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def get_activity(activity_id: int) -> Activity:
    """Return one activity or raise a 404 response."""
    return db.first_or_404(
        select(Activity).where(Activity.id == activity_id, private_scope(Activity))
    )


def create_activity(**values: Unpack[ActivityValues]) -> Activity:
    """Create and persist an activity."""
    activity = Activity()
    activity.owner_id = actor_id()
    _apply_values(activity, values)
    _prepare_activity(activity)
    db.session.add(activity)
    db.session.commit()
    return activity


def update_activity(activity: Activity, **values: Unpack[ActivityValues]) -> Activity:
    """Update and persist an activity."""
    require_private_record(activity)
    _apply_values(activity, values)
    _prepare_activity(activity)
    db.session.commit()
    return activity


def delete_activity(activity: Activity) -> None:
    """Delete an activity."""
    require_private_record(activity)
    db.session.delete(activity)
    db.session.commit()


def recent_activities(
    *,
    organization_id: int | None = None,
    contact_id: int | None = None,
    job_posting_id: int | None = None,
    application_id: int | None = None,
    limit: int = 5,
) -> list[Activity]:
    """Return recent activities for one detail-page context."""
    statement = select(Activity).where(private_scope(Activity))
    filters = {
        Activity.organization_id: organization_id,
        Activity.contact_id: contact_id,
        Activity.job_posting_id: job_posting_id,
        Activity.application_id: application_id,
    }
    for column, value in filters.items():
        if value is not None:
            statement = statement.where(column == value)
    return list(
        db.session.scalars(
            statement.order_by(Activity.occurred_at.desc(), Activity.id.desc()).limit(
                limit
            )
        )
    )


def latest_activities(limit: int = 5) -> list[Activity]:
    """Return the latest activities across the CRM."""
    if not inspect(db.engine).has_table(Activity.__tablename__):
        return []
    return list(
        db.session.scalars(
            select(Activity)
            .where(private_scope(Activity))
            .order_by(Activity.occurred_at.desc(), Activity.id.desc())
            .limit(limit)
        )
    )


def add_application_submitted_activity(application: Application) -> Activity | None:
    """Stage one predictable submission activity for a new submitted application."""
    if application.status not in SUBMITTED_STATUSES:
        return None
    job = db.session.get(JobPosting, application.job_posting_id)
    if job is None:
        return None
    occurred_at = (
        datetime.combine(application.application_date, time.min)
        if application.application_date
        else datetime.now(UTC)
    )
    activity = Activity(
        owner_id=application.owner_id,
        organization_id=job.organization_id,
        job_posting_id=job.id,
        application_id=application.id,
        activity_type=ActivityType.APPLICATION_SUBMITTED,
        occurred_at=occurred_at,
        direction=ActivityDirection.OUTBOUND,
        subject=f"Applied for {job.title}",
        summary="Application submitted.",
    )
    db.session.add(activity)
    return activity


def entity_choices() -> dict[str, list[tuple[int, str]]]:
    """Return ordered choices for forms and filters."""
    organizations = db.session.scalars(select(Organization).order_by(Organization.name))
    contacts = db.session.scalars(
        select(Contact)
        .where(private_scope(Contact))
        .order_by(Contact.last_name, Contact.first_name)
    )
    jobs = db.session.scalars(select(JobPosting).order_by(JobPosting.title))
    applications = db.session.scalars(
        select(Application)
        .join(Application.job_posting)
        .where(private_scope(Application))
        .order_by(JobPosting.title)
    )
    return {
        "organizations": [(item.id, item.name) for item in organizations],
        "contacts": [(item.id, item.full_name) for item in contacts],
        "jobs": [(item.id, item.title) for item in jobs],
        "applications": [(item.id, item.job_posting.title) for item in applications],
    }


def _apply_values(activity: Activity, values: ActivityValues) -> None:
    for field, value in values.items():
        if isinstance(value, str) and field not in {"activity_type", "direction"}:
            value = value.strip() or None
        setattr(activity, field, value)


def _prepare_activity(activity: Activity) -> None:
    if activity.application_id is not None:
        application = _require(Application, activity.application_id)
        activity.job_posting_id = activity.job_posting_id or application.job_posting_id
    if activity.job_posting_id is not None:
        job = _require(JobPosting, activity.job_posting_id)
        activity.organization_id = activity.organization_id or job.organization_id
    if activity.contact_id is not None:
        contact = _require(Contact, activity.contact_id)
        activity.organization_id = activity.organization_id or contact.organization_id
    if activity.organization_id is not None:
        _require(Organization, activity.organization_id)
    activity.validate_relationship()


def _require(model: type, entity_id: int):
    typed_model = cast(Any, model)
    statement: Any = select(model).where(typed_model.id == entity_id)
    if model in {Contact, Application}:
        statement = statement.where(private_scope(model))
    entity = db.session.scalar(statement)
    if entity is None:
        raise ValueError(f"Invalid {model.__name__.replace('_', ' ').lower()}.")
    return entity


def _apply_sort(
    statement: Select[tuple[Activity]], sort: str, direction: str
) -> Select[tuple[Activity]]:
    column = SORT_COLUMNS.get(sort, Activity.occurred_at)
    order = desc if direction == "desc" else asc
    return statement.order_by(order(column).nulls_last(), desc(Activity.id))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
