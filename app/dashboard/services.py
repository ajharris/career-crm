"""Queries used by the foundation dashboard."""

from app.applications.services import count_applications
from app.activities.services import latest_activities
from app.jobs.services import count_job_postings
from app.models.activity import Activity


def dashboard_statistics() -> tuple[tuple[str, int], ...]:
    """Return dashboard values implemented by current milestones."""
    return (
        ("Organizations", 0),
        ("Contacts", 0),
        ("Job Postings", count_job_postings()),
        ("Applications", count_applications()),
        ("Follow-ups", 0),
    )


def dashboard_recent_activities() -> list[Activity]:
    """Return the five most recent completed activities."""
    return latest_activities(limit=5)
