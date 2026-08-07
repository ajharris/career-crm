"""Forms for saved dashboard preferences."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField


class DashboardSettingsForm(FlaskForm):
    """Choose which analytics widgets appear on the dashboard."""

    pipeline = BooleanField("Pipeline by stage")
    tasks = BooleanField("Overdue tasks")
    deadlines = BooleanField("Upcoming deadlines")
    activity = BooleanField("Activity timeline")
    applications = BooleanField("Recent applications")
    interviews = BooleanField("Upcoming interviews")
    organizations = BooleanField("Organization statistics")
    analytics = BooleanField("Analytics summaries")
    submit = SubmitField("Save dashboard")
