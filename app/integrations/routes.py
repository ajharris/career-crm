"""Connected-account settings for authenticated Career CRM users."""

import secrets

from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.integrations import bp
from app.integrations.services import (
    authorization_url,
    connect,
    connection_for,
    disconnect,
    save_drive_folder,
)


@bp.get("")
def settings():
    return render_template(
        "integrations/settings.html",
        drive_connection=connection_for(current_user.id, "drive"),
        gmail_connection=connection_for(current_user.id, "gmail"),
    )


@bp.post("/google/<service>/connect")
def google_connect(service: str):
    redirect_uri = url_for(
        "integrations.google_callback", service=service, _external=True
    )
    google_email = request.form.get("google_email", "").strip()[:320] or None
    try:
        target, state = authorization_url(service, redirect_uri, google_email)
    except (RuntimeError, ValueError) as exc:
        flash(str(exc), "warning")
        return redirect(url_for("integrations.settings"))
    session[f"google_{service}_oauth_state"] = state
    session[f"google_{service}_expected_email"] = google_email
    return redirect(target)


@bp.get("/google/<service>/callback")
def google_callback(service: str):
    expected = session.pop(f"google_{service}_oauth_state", None)
    expected_email = session.pop(f"google_{service}_expected_email", None)
    if not expected or not secrets.compare_digest(expected, request.args.get("state", "")):
        abort(400)
    if error := request.args.get("error"):
        flash(f"Google account connection was not completed: {error}.", "warning")
        return redirect(url_for("integrations.settings"))
    try:
        connect(
            current_user.id,
            service,
            request.args.get("code", ""),
            url_for("integrations.google_callback", service=service, _external=True),
            expected_email,
        )
    except (RuntimeError, ValueError) as exc:
        flash(str(exc), "warning")
    else:
        flash(f"Google {service.title()} connected successfully.", "success")
    return redirect(url_for("integrations.settings"))


@bp.post("/google/folder")
def google_folder():
    try:
        save_drive_folder(current_user.id, request.form.get("folder_id"))
    except RuntimeError as exc:
        flash(str(exc), "warning")
    else:
        flash("Google Drive folder saved.", "success")
    return redirect(url_for("integrations.settings"))


@bp.post("/google/<service>/disconnect")
def google_disconnect(service: str):
    try:
        disconnect(current_user.id, service)
    except ValueError as exc:
        flash(str(exc), "warning")
    else:
        flash(f"Google {service.title()} disconnected.", "success")
    return redirect(url_for("integrations.settings"))
