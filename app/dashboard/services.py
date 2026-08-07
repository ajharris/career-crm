"""Queries used by the foundation dashboard."""

from app.applications.services import count_applications
from app.activities.services import latest_activities
from app.jobs.services import count_job_postings
from app.models.activity import Activity
from app.tasks.services import dashboard_tasks


def dashboard_statistics() -> tuple[tuple[str, int], ...]:
    """Return dashboard values implemented by current milestones."""
    return (
        ("Organizations", 0),
        ("Contacts", 0),
        ("Job Postings", count_job_postings()),
        ("Applications", count_applications()),
        ("Follow-ups", dashboard_tasks()["follow_ups"]),
    )


def dashboard_recent_activities() -> list[Activity]:
    """Return the five most recent completed activities."""
    return latest_activities(limit=5)


def dashboard_task_summary() -> dict:
    """Return actionable task counts and the next five due tasks."""
    return dashboard_tasks()
