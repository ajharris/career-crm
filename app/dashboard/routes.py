"""Dashboard routes."""

from flask import render_template

from app.dashboard import bp
from app.dashboard.services import dashboard_statistics


@bp.get("/")
def index() -> str:
    """Render the application dashboard."""
    return render_template(
        "dashboard/index.html", statistics=dashboard_statistics()
    )
