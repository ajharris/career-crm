from flask import redirect, render_template, request, url_for
from sqlalchemy import select

from app.auth.permissions import actor_id
from app.extensions import db
from app.models import NotificationDismissal
from app.notifications import bp
from app.notifications.services import notifications


@bp.get("")
def index():
    return render_template("notifications/index.html", notifications=notifications())


@bp.post("/dismiss")
def dismiss():
    key = request.form.get("key", "")[:160]
    existing = (
        db.session.scalar(
            select(NotificationDismissal.id).where(
                NotificationDismissal.owner_id == actor_id(),
                NotificationDismissal.notification_key == key,
            )
        )
        if key
        else None
    )
    if key and existing is None:
        db.session.add(NotificationDismissal(notification_key=key))
        db.session.commit()
    return redirect(url_for("notifications.index"))
