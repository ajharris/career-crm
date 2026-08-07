"""Compute local reminders from current CRM state."""

from datetime import date, timedelta

from sqlalchemy import select

from app.auth.permissions import actor_id
from app.extensions import db
from app.models import Application, JobPosting, NotificationDismissal, Task
from app.utils.enums import TaskStatus


def notifications():
    today = date.today()
    items = []
    tasks = db.session.scalars(
        select(Task)
        .where(
            Task.owner_id == actor_id(),
            Task.status != TaskStatus.COMPLETED,
            Task.due_date <= today + timedelta(days=1),
        )
        .order_by(Task.due_date)
    )
    for task in tasks:
        if task.due_date is None:
            continue
        label = (
            "overdue"
            if task.due_date < today
            else "due today" if task.due_date == today else "due tomorrow"
        )
        items.append(
            {
                "key": f"task:{task.id}:{task.due_date}",
                "level": "danger" if label == "overdue" else "warning",
                "title": task.title,
                "message": f"Task {label}.",
                "url": f"/tasks/{task.id}/edit",
            }
        )
    applications = db.session.scalars(
        select(Application).where(
            Application.owner_id == actor_id(), Application.interview_date.is_not(None)
        )
    )
    for application in applications:
        if application.interview_date is None:
            continue
        when = application.interview_date.date()
        if when == today:
            items.append(
                {
                    "key": f"interview:{application.id}:{when}",
                    "level": "primary",
                    "title": application.job_posting.title,
                    "message": "Interview today.",
                    "url": f"/applications/{application.id}",
                }
            )
    jobs = db.session.scalars(
        select(JobPosting).where(
            JobPosting.closing_date.between(today, today + timedelta(days=3))
        )
    )
    for job in jobs:
        items.append(
            {
                "key": f"deadline:{job.id}:{job.closing_date}",
                "level": "warning",
                "title": job.title,
                "message": f"Application deadline {job.closing_date:%b %d}.",
                "url": f"/jobs/{job.id}",
            }
        )
    dismissed = set(
        db.session.scalars(
            select(NotificationDismissal.notification_key).where(
                NotificationDismissal.owner_id == actor_id()
            )
        )
    )
    return [item for item in items if item["key"] not in dismissed]
