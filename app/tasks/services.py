"""Business operations and queries for tasks."""

from datetime import UTC, date, datetime
from typing import TypedDict, Unpack

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import case, inspect, or_, select

from app.extensions import db
from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.models.task import Task
from app.utils.enums import (
    ActivityDirection,
    ActivityType,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class TaskValues(TypedDict, total=False):
    organization_id: int | None
    contact_id: int | None
    job_posting_id: int | None
    application_id: int | None
    title: str
    description: str | None
    task_type: str
    priority: str
    status: str
    due_date: date | None
    due_time: object | None


ACTIVE = {TaskStatus.OPEN, TaskStatus.IN_PROGRESS}
SORT_COLUMNS = {
    "due_date": Task.due_date,
    "status": Task.status,
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "completed_at": Task.completed_at,
}
PRIORITY_ORDER = case(
    (Task.priority == TaskPriority.URGENT, 0),
    (Task.priority == TaskPriority.HIGH, 1),
    (Task.priority == TaskPriority.MEDIUM, 2),
    else_=3,
)


def list_tasks(
    *,
    search="",
    status="",
    priority="",
    task_type="",
    organization_id=None,
    contact_id=None,
    due_from=None,
    due_to=None,
    overdue=False,
    completed_only=False,
    sort="actionable",
    sort_direction="asc",
    page=1,
) -> Pagination:
    """Return a filtered page of tasks; hide terminal tasks by default."""
    statement = (
        select(Task)
        .outerjoin(Task.organization)
        .outerjoin(Task.contact)
        .outerjoin(Task.job_posting)
    )
    if search := search.strip():
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
                Organization.name.ilike(pattern),
                Contact.first_name.ilike(pattern),
                Contact.last_name.ilike(pattern),
                JobPosting.title.ilike(pattern),
            )
        )
    if completed_only:
        statement = statement.where(Task.status == TaskStatus.COMPLETED)
    elif status:
        statement = statement.where(Task.status == status)
    else:
        statement = statement.where(Task.status.in_(ACTIVE))
    for column, value in (
        (Task.priority, priority),
        (Task.task_type, task_type),
        (Task.organization_id, organization_id),
        (Task.contact_id, contact_id),
    ):
        if value not in (None, ""):
            statement = statement.where(column == value)
    if due_from:
        statement = statement.where(Task.due_date >= due_from)
    if due_to:
        statement = statement.where(Task.due_date <= due_to)
    if overdue:
        statement = statement.where(
            Task.status.in_(ACTIVE), Task.due_date < date.today()
        )
    direction = "desc" if sort_direction == "desc" else "asc"
    if sort == "priority":
        order = getattr(PRIORITY_ORDER, direction)()
    elif sort in SORT_COLUMNS:
        order = getattr(SORT_COLUMNS[sort], direction)().nulls_last()
    else:
        overdue_order = case((Task.due_date < date.today(), 0), else_=1)
        statement = statement.order_by(
            overdue_order, Task.due_date.asc().nulls_last(), PRIORITY_ORDER
        )
        order = Task.created_at.asc()
    statement = statement.order_by(order, Task.id.desc())
    return db.paginate(statement, page=max(page, 1), per_page=25, error_out=False)


def get_task(task_id: int) -> Task:
    return db.get_or_404(Task, task_id)


def create_task(**values: Unpack[TaskValues]) -> Task:
    task = Task()
    _apply(task, values)
    db.session.add(task)
    db.session.commit()
    return task


def update_task(task: Task, **values: Unpack[TaskValues]) -> Task:
    _apply(task, values)
    db.session.commit()
    return task


def delete_task(task: Task) -> None:
    db.session.delete(task)
    db.session.commit()


def complete_task(task: Task) -> Task:
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)
    activity_types = {
        TaskType.FOLLOW_UP: ActivityType.FOLLOW_UP,
        TaskType.NETWORKING: ActivityType.NETWORKING,
        TaskType.THANK_YOU: ActivityType.EMAIL,
    }
    if task.task_type in activity_types and any(
        (
            task.organization_id,
            task.contact_id,
            task.job_posting_id,
            task.application_id,
        )
    ):
        db.session.add(
            Activity(
                organization_id=task.organization_id,
                contact_id=task.contact_id,
                job_posting_id=task.job_posting_id,
                application_id=task.application_id,
                activity_type=activity_types[task.task_type],
                occurred_at=task.completed_at,
                direction=ActivityDirection.OUTBOUND,
                subject=task.title,
                summary="Completed from a CRM task.",
            )
        )
    db.session.commit()
    return task


def reopen_task(task: Task) -> Task:
    task.status = TaskStatus.OPEN
    task.completed_at = None
    db.session.commit()
    return task


def context_tasks(
    *,
    organization_id=None,
    contact_id=None,
    job_posting_id=None,
    application_id=None,
    completed=False,
    limit=5,
) -> list[Task]:
    statement = select(Task)
    for column, value in (
        (Task.organization_id, organization_id),
        (Task.contact_id, contact_id),
        (Task.job_posting_id, job_posting_id),
        (Task.application_id, application_id),
    ):
        if value is not None:
            statement = statement.where(column == value)
    statement = statement.where(
        Task.status == TaskStatus.COMPLETED if completed else Task.status.in_(ACTIVE)
    )
    return list(
        db.session.scalars(
            statement.order_by(Task.due_date.asc().nulls_last(), Task.id.desc()).limit(
                limit
            )
        )
    )


def dashboard_tasks() -> dict:
    if not inspect(db.engine).has_table(Task.__tablename__):
        return {"open": 0, "overdue": 0, "today": 0, "follow_ups": 0, "upcoming": []}
    active = select(Task).where(Task.status.in_(ACTIVE))
    all_active = list(db.session.scalars(active))
    today = date.today()
    upcoming = list(
        db.session.scalars(
            active.where(Task.due_date >= today)
            .order_by(Task.due_date, PRIORITY_ORDER)
            .limit(5)
        )
    )
    return {
        "open": len(all_active),
        "overdue": sum(t.is_overdue for t in all_active),
        "today": sum(t.due_date == today for t in all_active),
        "follow_ups": sum(t.task_type == TaskType.FOLLOW_UP for t in all_active),
        "upcoming": upcoming,
    }


def _apply(task: Task, values: TaskValues) -> None:
    for field, value in values.items():
        if isinstance(value, str) and field not in {"task_type", "priority", "status"}:
            value = value.strip() or None
        setattr(task, field, value)
    if task.due_time and not task.due_date:
        raise ValueError("A due date is required when a due time is set.")
    if task.application_id:
        entity = _require(Application, task.application_id)
        task.job_posting_id = task.job_posting_id or entity.job_posting_id
    if task.job_posting_id:
        entity = _require(JobPosting, task.job_posting_id)
        task.organization_id = task.organization_id or entity.organization_id
    if task.contact_id:
        entity = _require(Contact, task.contact_id)
        task.organization_id = task.organization_id or entity.organization_id
    if task.organization_id:
        _require(Organization, task.organization_id)


def _require(model, entity_id):
    entity = db.session.get(model, entity_id)
    if entity is None:
        raise ValueError(f"Invalid {model.__name__.lower()}.")
    return entity
