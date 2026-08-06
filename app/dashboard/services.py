# app/dashboard/services.py

from datetime import date

from sqlalchemy import func, select

from app.extensions import db
from app.models import Application, JobPosting, Task


def get_dashboard_data() -> dict:
    application_count = db.session.scalar(
        select(func.count(Application.id))
    )

    active_jobs = db.session.scalar(
        select(func.count(JobPosting.id))
        .where(JobPosting.status.not_in(["closed", "skipped"]))
    )

    overdue_tasks = list(
        db.session.scalars(
            select(Task)
            .where(
                Task.completed_at.is_(None),
                Task.due_date < date.today(),
            )
            .order_by(Task.due_date)
        )
    )

    return {
        "application_count": application_count or 0,
        "active_jobs": active_jobs or 0,
        "overdue_tasks": overdue_tasks,
    }