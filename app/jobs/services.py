"""Business operations and queries for job postings."""

from datetime import date, datetime
from decimal import Decimal
from typing import TypedDict, Unpack

from flask import abort
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, func, inspect, or_, select

from app.auth.permissions import actor_id, private_scope, require_shared_editor
from app.extensions import db
from app.models.activity import Activity
from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.models.task import Task
from app.utils.enums import JobStatus


class JobPostingValues(TypedDict, total=False):
    """Values accepted when creating or updating a job posting."""

    organization_id: int
    title: str
    department: str | None
    location: str | None
    employment_type: str | None
    work_mode: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    posting_url: str | None
    source: str | None
    date_posted: date | None
    closing_date: date | None
    discovered_at: datetime | None
    priority: int
    status: str
    description: str | None
    notes: str | None


SORT_COLUMNS = {
    "title": JobPosting.title,
    "organization": Organization.name,
    "priority": JobPosting.priority,
    "closing_date": JobPosting.closing_date,
    "date_posted": JobPosting.date_posted,
    "discovered_at": JobPosting.discovered_at,
    "created_at": JobPosting.created_at,
}


def list_job_postings(
    *,
    search: str = "",
    organization_id: int | None = None,
    status: str = "",
    employment_type: str = "",
    work_mode: str = "",
    priority: int | None = None,
    sort: str = "created_at",
    direction: str = "desc",
    page: int = 1,
) -> Pagination:
    """Return a searched, filtered, sorted page of job postings."""
    statement = select(JobPosting).join(JobPosting.organization)
    if search := search.strip():
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                JobPosting.title.ilike(pattern, escape="\\"),
                Organization.name.ilike(pattern, escape="\\"),
                JobPosting.department.ilike(pattern, escape="\\"),
                JobPosting.description.ilike(pattern, escape="\\"),
                JobPosting.notes.ilike(pattern, escape="\\"),
            )
        )
    if organization_id is not None:
        statement = statement.where(JobPosting.organization_id == organization_id)
    if status:
        statement = statement.where(JobPosting.status == status)
    if employment_type:
        statement = statement.where(JobPosting.employment_type == employment_type)
    if work_mode:
        statement = statement.where(JobPosting.work_mode == work_mode)
    if priority is not None:
        statement = statement.where(JobPosting.priority == priority)
    statement = _apply_sort(statement, sort, direction)
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def active_jobs_for_organization(organization_id: int) -> list[JobPosting]:
    """Return non-closed job postings for an organization."""
    return list(
        db.session.scalars(
            select(JobPosting)
            .where(
                JobPosting.organization_id == organization_id,
                JobPosting.status.not_in([JobStatus.CLOSED, JobStatus.SKIPPED]),
            )
            .order_by(JobPosting.closing_date.asc().nulls_last(), JobPosting.title)
        )
    )


def count_job_postings() -> int:
    """Return the total number of job postings."""
    if not inspect(db.engine).has_table(JobPosting.__tablename__):
        return 0
    return db.session.scalar(select(func.count(JobPosting.id))) or 0


def get_job_posting(job_id: int) -> JobPosting:
    """Return one job posting or raise a 404 response."""
    return db.get_or_404(JobPosting, job_id)


def create_job_posting(**values: Unpack[JobPostingValues]) -> JobPosting:
    """Create and persist a job posting."""
    job = JobPosting()
    job.created_by_id = actor_id()
    job.updated_by_id = job.created_by_id
    _apply_values(job, values)
    _validate_job(job)
    db.session.add(job)
    db.session.commit()
    return job


def update_job_posting(
    job: JobPosting, **values: Unpack[JobPostingValues]
) -> JobPosting:
    """Update and persist a job posting."""
    require_shared_editor(job)
    _apply_values(job, values)
    job.updated_by_id = actor_id()
    _validate_job(job)
    db.session.commit()
    return job


def delete_job_posting(job: JobPosting) -> None:
    """Delete a job posting."""
    require_shared_editor(job)
    owner_id = actor_id()
    private_records = (
        select(Application.id).where(
            Application.job_posting_id == job.id, Application.owner_id != owner_id
        ),
        select(Activity.id).where(
            Activity.owner_id != owner_id,
            or_(
                Activity.job_posting_id == job.id,
                Activity.application.has(Application.job_posting_id == job.id),
            ),
        ),
        select(Task.id).where(
            Task.owner_id != owner_id,
            or_(
                Task.job_posting_id == job.id,
                Task.application.has(Application.job_posting_id == job.id),
            ),
        ),
    )
    if any(db.session.scalar(statement.limit(1)) for statement in private_records):
        abort(
            409,
            description=(
                "This job posting contains another user's private history and "
                "cannot be deleted."
            ),
        )
    db.session.delete(job)
    db.session.commit()


def organization_choices() -> list[tuple[int, str]]:
    """Return organizations ordered for selection controls."""
    organizations = db.session.scalars(
        select(Organization).order_by(Organization.name)
    ).all()
    return [(organization.id, organization.name) for organization in organizations]


def application_for_job(job_id: int) -> Application | None:
    """Return only the current user's application for a shared job."""
    return db.session.scalar(
        select(Application).where(
            Application.job_posting_id == job_id, private_scope(Application)
        )
    )


def _apply_values(job: JobPosting, values: JobPostingValues) -> None:
    for field, value in values.items():
        if field == "discovered_at" and value is None:
            continue
        if field != "title" and isinstance(value, str):
            value = value.strip() or None
        setattr(job, field, value)


def _validate_job(job: JobPosting) -> None:
    if db.session.get(Organization, job.organization_id) is None:
        raise ValueError("A valid organization is required.")
    job.validate_ranges()


def _apply_sort(
    statement: Select[tuple[JobPosting]], sort: str, direction: str
) -> Select[tuple[JobPosting]]:
    column = SORT_COLUMNS.get(sort, JobPosting.created_at)
    order = desc if direction == "desc" else asc
    primary_order = order(column)
    if sort in {"closing_date", "date_posted"}:
        primary_order = primary_order.nulls_last()
    return statement.order_by(primary_order, asc(JobPosting.title), asc(JobPosting.id))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
