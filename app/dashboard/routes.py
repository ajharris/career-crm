"""Dashboard routes."""

from flask import render_template

from app.dashboard import bp


@bp.get("/")
def index() -> str:
    """Render the application dashboard."""
    statistics = (
        ("Organizations", 0),
        ("Contacts", 0),
        ("Job Postings", 0),
        ("Applications", 0),
        ("Follow-ups", 0),
    )
    return render_template("dashboard/index.html", statistics=statistics)
