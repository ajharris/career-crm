"""Dashboard routes."""

from flask import render_template

from app.dashboard import bp
from app.dashboard.services import dashboard_data


@bp.get("/")
def index() -> str:
    """Render the read-only job-search command center."""
    return render_template("dashboard/index.html", **dashboard_data())
