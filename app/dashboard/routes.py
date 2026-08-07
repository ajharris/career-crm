"""Dashboard routes."""

from flask import flash, redirect, render_template, request, url_for

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
    from app.profile.services import (
        get_profile,
        profile_completeness,
        profile_summary,
        should_show_profile_reminder,
    )

    profile = get_profile()

    return render_template(
        "dashboard/index.html",
        profile_summary=profile_summary(),
        profile_completion=profile_completeness(profile),
        show_profile_reminder=should_show_profile_reminder(profile),
        **dashboard_data(),
    )


@bp.post("/dashboard/profile-reminder")
def profile_reminder():
    from app.profile.services import set_reminder

    try:
        set_reminder(request.form.get("interval", "one_week"))
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("dashboard.index"))


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
