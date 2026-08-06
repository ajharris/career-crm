"""Queries used by the foundation dashboard."""

from app.jobs.services import count_job_postings


def dashboard_statistics() -> tuple[tuple[str, int], ...]:
    """Return dashboard values implemented by current milestones."""
    return (
        ("Organizations", 0),
        ("Contacts", 0),
        ("Job Postings", count_job_postings()),
        ("Applications", 0),
        ("Follow-ups", 0),
    )
