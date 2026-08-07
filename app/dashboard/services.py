"""Read-only analytics queries for the dashboard."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import distinct, func, inspect, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.models.task import Task
from app.utils.enums import (
    ActivityType,
    ApplicationStatus,
    JobStatus,
    TaskStatus,
)


ACTIVE_TASK_STATUSES = (TaskStatus.OPEN, TaskStatus.IN_PROGRESS)
ACTIVE_JOB_STATUSES = (
    JobStatus.DISCOVERED,
    JobStatus.RESEARCHING,
    JobStatus.READY_TO_APPLY,
    JobStatus.APPLIED,
)


def dashboard_data(today: date | None = None) -> dict:
    """Return every value needed to render the dashboard."""
    table_names = inspect(db.engine).get_table_names()
    required_tables = {
        Organization.__tablename__,
        Contact.__tablename__,
        JobPosting.__tablename__,
        Application.__tablename__,
        Activity.__tablename__,
        Task.__tablename__,
    }
    if not required_tables.issubset(table_names):
        return _empty_dashboard()
    today = today or date.today()
    now = datetime.now(UTC)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    task_groups = _task_groups(today, week_end)
    pipeline = _pipeline()
    recent_activities = list(
        db.session.scalars(
            select(Activity)
            .options(joinedload(Activity.organization))
            .order_by(Activity.occurred_at.desc(), Activity.id.desc())
            .limit(10)
        )
    )
    recent_applications = list(
        db.session.scalars(
            select(Application)
            .options(
                joinedload(Application.job_posting).joinedload(
                    JobPosting.organization
                )
            )
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(10)
        ).unique()
    )
    upcoming_interviews = list(
        db.session.scalars(
            select(Application)
            .options(
                joinedload(Application.job_posting).joinedload(
                    JobPosting.organization
                )
            )
            .where(Application.interview_date >= now)
            .order_by(Application.interview_date, Application.id)
            .limit(10)
        ).unique()
    )

    activities_by_type = dict(
        db.session.execute(
            select(Activity.activity_type, func.count(Activity.id))
            .group_by(Activity.activity_type)
            .order_by(func.count(Activity.id).desc(), Activity.activity_type)
        ).all()
    )
    top_organizations = db.session.execute(
        select(Organization, func.count(Activity.id).label("activity_count"))
        .join(Activity, Activity.organization_id == Organization.id)
        .group_by(Organization.id)
        .order_by(func.count(Activity.id).desc(), Organization.name)
        .limit(10)
    ).all()

    summary_cards = (
        ("Organizations", _count(Organization.id), "organizations.index", "▦"),
        ("Contacts", _count(Contact.id), "contacts.index", "♙"),
        (
            "Job Postings",
            _count(JobPosting.id, JobPosting.status.in_(ACTIVE_JOB_STATUSES)),
            "jobs.index",
            "▤",
        ),
        ("Applications", _count(Application.id), "applications.index", "✓"),
        (
            "Open Tasks",
            _count(Task.id, Task.status.in_(ACTIVE_TASK_STATUSES)),
            "tasks.index",
            "☑",
        ),
        (
            "Overdue Tasks",
            _count(
                Task.id,
                Task.status.in_(ACTIVE_TASK_STATUSES),
                Task.due_date < today,
            ),
            "tasks.index",
            "!",
        ),
    )

    return {
        "summary_cards": summary_cards,
        "pipeline": pipeline,
        "pipeline_total": sum(item[1] for item in pipeline),
        "task_groups": task_groups,
        "recent_activities": recent_activities,
        "recent_applications": recent_applications,
        "upcoming_interviews": upcoming_interviews,
        "top_organizations": top_organizations,
        "job_summary": {
            "active": _count(
                JobPosting.id, JobPosting.status.in_(ACTIVE_JOB_STATUSES)
            ),
            "closed": _count(JobPosting.id, JobPosting.status == JobStatus.CLOSED),
            "applied": _count(JobPosting.id, JobPosting.status == JobStatus.APPLIED),
        },
        "activity_summary": {
            "week": _count(
                Activity.id,
                Activity.occurred_at >= _start_of(week_start),
                Activity.occurred_at < _start_of(today + timedelta(days=1)),
            ),
            "month": _count(
                Activity.id,
                Activity.occurred_at >= _start_of(month_start),
                Activity.occurred_at < _start_of(today + timedelta(days=1)),
            ),
            "by_type": activities_by_type,
        },
        "productivity": {
            "tasks_completed_week": _count(
                Task.id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= _start_of(week_start),
                Task.completed_at < _start_of(today + timedelta(days=1)),
            ),
            "applications_submitted_month": _count(
                Application.id,
                Application.application_date >= month_start,
                Application.application_date <= today,
                Application.status.not_in(
                    (ApplicationStatus.PLANNED, ApplicationStatus.PREPARING)
                ),
            ),
            "organizations_contacted_month": _count(
                distinct(Activity.organization_id),
                Activity.organization_id.is_not(None),
                Activity.occurred_at >= _start_of(month_start),
                Activity.occurred_at < _start_of(today + timedelta(days=1)),
            ),
            "interviews_completed_year": _count(
                Activity.id,
                Activity.activity_type == ActivityType.INTERVIEW,
                Activity.occurred_at >= _start_of(year_start),
                Activity.occurred_at <= now,
            ),
        },
    }


def _task_groups(today: date, week_end: date) -> dict[str, list[Task]]:
    tasks = list(
        db.session.scalars(
            select(Task)
            .options(joinedload(Task.organization))
            .where(
                Task.status.in_(ACTIVE_TASK_STATUSES),
                Task.due_date.is_not(None),
                Task.due_date <= week_end,
            )
            .order_by(Task.due_date, Task.priority.desc(), Task.id)
            .limit(10)
        )
    )
    return {
        "overdue": [task for task in tasks if task.due_date < today],
        "today": [task for task in tasks if task.due_date == today],
        "week": [task for task in tasks if today < task.due_date <= week_end],
    }


def _pipeline() -> list[tuple[ApplicationStatus, int]]:
    counts = dict(
        db.session.execute(
            select(Application.status, func.count(Application.id)).group_by(
                Application.status
            )
        ).all()
    )
    return [(status, counts.get(status, 0)) for status in ApplicationStatus]


def _count(column, *criteria) -> int:
    return db.session.scalar(select(func.count(column)).where(*criteria)) or 0


def _start_of(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _empty_dashboard() -> dict:
    """Keep the dashboard useful before a development database is initialized."""
    return {
        "summary_cards": (
            ("Organizations", 0, "organizations.index", "▦"),
            ("Contacts", 0, "contacts.index", "♙"),
            ("Job Postings", 0, "jobs.index", "▤"),
            ("Applications", 0, "applications.index", "✓"),
            ("Open Tasks", 0, "tasks.index", "☑"),
            ("Overdue Tasks", 0, "tasks.index", "!"),
        ),
        "pipeline": [(status, 0) for status in ApplicationStatus],
        "pipeline_total": 0,
        "task_groups": {"overdue": [], "today": [], "week": []},
        "recent_activities": [],
        "recent_applications": [],
        "upcoming_interviews": [],
        "top_organizations": [],
        "job_summary": {"active": 0, "closed": 0, "applied": 0},
        "activity_summary": {"week": 0, "month": 0, "by_type": {}},
        "productivity": {
            "tasks_completed_week": 0,
            "applications_submitted_month": 0,
            "organizations_contacted_month": 0,
            "interviews_completed_year": 0,
        },
    }


# Compatibility helpers retained for callers from earlier milestones.
def dashboard_statistics() -> tuple[tuple[str, int], ...]:
    return tuple((label, count) for label, count, _, _ in dashboard_data()["summary_cards"])


def dashboard_recent_activities() -> list[Activity]:
    return dashboard_data()["recent_activities"]


def dashboard_task_summary() -> dict:
    data = dashboard_data()
    groups = data["task_groups"]
    return {
        "open": next(x[1] for x in data["summary_cards"] if x[0] == "Open Tasks"),
        "overdue": len(groups["overdue"]),
        "today": len(groups["today"]),
        "upcoming": groups["week"],
    }
