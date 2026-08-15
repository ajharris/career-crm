"""Administrator-only instance storage settings routes."""

import secrets

from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.storage import bp
from app.storage.services import (
    configuration,
    connect,
    disconnect,
    oauth_authorization_url,
    set_folder,
)


def _require_admin() -> None:
    if not current_user.is_admin:
        abort(403)


@bp.get("")
def settings():
    _require_admin()
    return render_template("storage/settings.html", storage=configuration())


@bp.post("/connect/google-drive")
def google_drive_connect():
    _require_admin()
    redirect_uri = url_for("storage.google_drive_callback", _external=True)
    try:
        authorization_url, state = oauth_authorization_url(redirect_uri)
    except RuntimeError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("storage.settings"))
    session["google_drive_oauth_state"] = state
    return redirect(authorization_url)


@bp.get("/callback/google-drive")
def google_drive_callback():
    _require_admin()
    expected = session.pop("google_drive_oauth_state", None)
    if not expected or not secrets.compare_digest(expected, request.args.get("state", "")):
        abort(400)
    if error := request.args.get("error"):
        flash(f"Google Drive connection was not completed: {error}.", "warning")
        return redirect(url_for("storage.settings"))
    try:
        connect(
            request.args.get("code", ""),
            url_for("storage.google_drive_callback", _external=True),
        )
    except RuntimeError as exc:
        flash(str(exc), "warning")
    else:
        flash("Google Drive is now the instance document storage provider.", "success")
    return redirect(url_for("storage.settings"))


@bp.post("/folder")
def folder():
    _require_admin()
    set_folder(request.form.get("folder_id"))
    flash("Google Drive folder saved.", "success")
    return redirect(url_for("storage.settings"))


@bp.post("/disconnect")
def storage_disconnect():
    _require_admin()
    disconnect()
    flash("Google Drive disconnected; new documents will use local storage.", "success")
    return redirect(url_for("storage.settings"))
