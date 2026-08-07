from flask import flash, render_template, request
from sqlalchemy import select

from app.ai import bp
from app.ai.services import generate
from app.auth.permissions import actor_id
from app.extensions import db
from app.models import Application


@bp.route("", methods=["GET", "POST"])
def index():
    applications = list(
        db.session.scalars(
            select(Application)
            .where(Application.owner_id == actor_id())
            .order_by(Application.updated_at.desc())
        )
    )
    result = None
    if request.method == "POST":
        application = db.session.scalar(
            select(Application).where(
                Application.id == request.form.get("application_id", type=int),
                Application.owner_id == actor_id(),
            )
        )
        if application:
            context = {
                "job": application.job_posting.title,
                "organization": application.job_posting.organization.name,
                "description": application.job_posting.description or "",
                "user_notes": request.form.get("notes", "")[:4000],
            }
            try:
                result = generate(request.form.get("task", "job_summary"), context)
            except (RuntimeError, ValueError) as exc:
                flash(str(exc), "warning")
    return render_template("ai/index.html", applications=applications, result=result)
