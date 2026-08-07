"""Dashboard routes."""

from flask import flash, redirect, render_template, url_for

from app.dashboard import bp
from app.dashboard.forms import DashboardSettingsForm
from app.dashboard.services import (
    WIDGETS,
    dashboard_data,
    get_widget_preferences,
    save_widget_preferences,
)


@bp.get("/")
def index() -> str:
    """Render the read-only job-search command center."""
    return render_template("dashboard/index.html", **dashboard_data())


@bp.route("/dashboard/settings", methods=["GET", "POST"])
def settings():
    """Edit the persisted dashboard widget selection."""
    form = DashboardSettingsForm()
    if form.validate_on_submit():
        enabled = {key for key, _ in WIDGETS if getattr(form, key).data}
        save_widget_preferences(enabled)
        flash("Dashboard widgets saved.", "success")
        return redirect(url_for("dashboard.index"))
    if not form.is_submitted():
        for preference in get_widget_preferences():
            getattr(form, preference["key"]).data = preference["enabled"]
    return render_template("dashboard/settings.html", form=form)
