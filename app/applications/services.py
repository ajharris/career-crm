"""Business operations and queries for applications."""

from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict, Unpack

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, extract, func, inspect, or_, select
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import actor_id, private_scope, require_private_record
from app.extensions import db
from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.organization import Organization


class DuplicateApplicationError(ValueError):
    """Raised when a job posting already has an application."""


class ApplicationValues(TypedDict, total=False):
    """Values accepted when creating or updating an application."""

    job_posting_id: int
    application_date: date | None
    status: str
    source: str | None
    resume_version: str | None
    cover_letter_version: str | None
    recruiter_name: str | None
    recruiter_email: str | None
    salary_requested: Decimal | None
    interview_date: datetime | None
    interview_location: str | None
    rejection_reason: str | None
    offer_salary: Decimal | None
    accepted: bool
    withdrawn: bool
    notes: str | None


SORT_COLUMNS = {
    "application_date": Application.application_date,
    "status": Application.status,
    "organization": Organization.name,
    "job_title": JobPosting.title,
    "interview_date": Application.interview_date,
    "updated_at": Application.updated_at,
}


def list_applications(
    *,
    search: str = "",
    status: str = "",
    organization_id: int | None = None,
    applied_year: int | None = None,
    accepted: bool | None = None,
    withdrawn: bool | None = None,
    sort: str = "updated_at",
    direction: str = "desc",
    page: int = 1,
) -> Pagination:
    """Return a searched, filtered, sorted page of applications."""
    statement = (
        select(Application)
        .join(Application.job_posting)
        .join(JobPosting.organization)
        .where(private_scope(Application))
    )
    if search := search.strip():
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                Organization.name.ilike(pattern, escape="\\"),
                JobPosting.title.ilike(pattern, escape="\\"),
                Application.recruiter_name.ilike(pattern, escape="\\"),
                Application.resume_version.ilike(pattern, escape="\\"),
                Application.notes.ilike(pattern, escape="\\"),
            )
        )
    if status:
        statement = statement.where(Application.status == status)
    if organization_id is not None:
        statement = statement.where(JobPosting.organization_id == organization_id)
    if applied_year is not None:
        statement = statement.where(
            extract("year", Application.application_date) == applied_year
        )
    if accepted is not None:
        statement = statement.where(Application.accepted.is_(accepted))
    if withdrawn is not None:
        statement = statement.where(Application.withdrawn.is_(withdrawn))
    statement = _apply_sort(statement, sort, direction)
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def get_application(application_id: int) -> Application:
    """Return one application or raise a 404 response."""
    return db.first_or_404(
        select(Application).where(
            Application.id == application_id, private_scope(Application)
        )
    )


def create_application(**values: Unpack[ApplicationValues]) -> Application:
    """Create and persist an application."""
    application = Application()
    application.owner_id = actor_id()
    _apply_values(application, values)
    _validate_application(application)
    db.session.add(application)
    _commit(application, add_submission_activity=True)
    return application


def update_application(
    application: Application, **values: Unpack[ApplicationValues]
) -> Application:
    """Update and persist an application."""
    require_private_record(application)
    _apply_values(application, values)
    _validate_application(application)
    _commit(application)
    return application


def delete_application(application: Application) -> None:
    """Delete an application."""
    require_private_record(application)
    db.session.delete(application)
    db.session.commit()


def available_job_choices(
    current_application: Application | None = None,
) -> list[tuple[int, str]]:
    """Return unapplied jobs, plus the current selection while editing."""
    statement = select(JobPosting).join(JobPosting.organization)
    owner_id = actor_id()
    if current_application is None:
        statement = statement.where(
            ~JobPosting.applications.any(Application.owner_id == owner_id)
        )
    else:
        require_private_record(current_application)
        statement = statement.where(
            or_(
                ~JobPosting.applications.any(Application.owner_id == owner_id),
                JobPosting.id == current_application.job_posting_id,
            )
        )
    jobs = db.session.scalars(
        statement.order_by(Organization.name, JobPosting.title)
    ).all()
    return [(job.id, f"{job.organization.name} — {job.title}") for job in jobs]


def organization_choices() -> list[tuple[int, str]]:
    """Return organizations ordered for filtering."""
    organizations = db.session.scalars(
        select(Organization).order_by(Organization.name)
    ).all()
    return [(organization.id, organization.name) for organization in organizations]


def applied_year_choices() -> list[int]:
    """Return distinct application years in descending order."""
    years = db.session.scalars(
        select(extract("year", Application.application_date))
        .where(private_scope(Application), Application.application_date.is_not(None))
        .distinct()
        .order_by(extract("year", Application.application_date).desc())
    ).all()
    return [int(year) for year in years]


def count_applications() -> int:
    """Return the total application count, including before schema setup."""
    if not inspect(db.engine).has_table(Application.__tablename__):
        return 0
    return (
        db.session.scalar(
            select(func.count(Application.id)).where(private_scope(Application))
        )
        or 0
    )


def _apply_values(application: Application, values: ApplicationValues) -> None:
    for field, value in values.items():
        if isinstance(value, str) and field != "status":
            value = value.strip() or None
        setattr(application, field, value)


def _validate_application(application: Application) -> None:
    if db.session.get(JobPosting, application.job_posting_id) is None:
        raise ValueError("A valid job posting is required.")
    application.validate_business_rules()


def _commit(application: Application, *, add_submission_activity: bool = False) -> None:
    try:
        db.session.flush()
        if add_submission_activity:
            from app.activities.services import add_application_submitted_activity

            add_application_submitted_activity(application)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        error_text = str(exc.orig).lower()
        if "job_posting_id" in error_text or "uq_applications_owner" in error_text:
            raise DuplicateApplicationError(
                f"Job posting {application.job_posting_id} already has an application."
            ) from exc
        raise


def _apply_sort(
    statement: Select[tuple[Application]], sort: str, direction: str
) -> Select[tuple[Application]]:
    column = SORT_COLUMNS.get(sort, Application.updated_at)
    order = desc if direction == "desc" else asc
    primary_order = order(column)
    if sort in {"application_date", "interview_date"}:
        primary_order = primary_order.nulls_last()
    return statement.order_by(primary_order, asc(Application.id))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
