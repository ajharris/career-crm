"""Dashboard routes."""

from flask import render_template

from app.dashboard import bp
from app.dashboard.services import (
    dashboard_recent_activities,
    dashboard_statistics,
    dashboard_task_summary,
)


@bp.get("/")
def index() -> str:
    """Render the application dashboard."""
    return render_template(
        "dashboard/index.html",
        statistics=dashboard_statistics(),
        recent_activities=dashboard_recent_activities(),
        task_summary=dashboard_task_summary(),
    )
