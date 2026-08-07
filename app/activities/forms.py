"""Forms used by activity management views."""

from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired, Length, Optional

from app.utils.enums import ActivityDirection, ActivityType


def optional_int(value: str | int | None) -> int | None:
    """Coerce an optional select value to an integer identifier."""
    return int(value) if value not in {None, ""} else None


class ActivityForm(FlaskForm):
    """Create or update an activity."""

    organization_id = SelectField(
        "Organization", coerce=optional_int, validators=[Optional()]
    )
    contact_id = SelectField("Contact", coerce=optional_int, validators=[Optional()])
    job_posting_id = SelectField(
        "Job posting", coerce=optional_int, validators=[Optional()]
    )
    application_id = SelectField(
        "Application", coerce=optional_int, validators=[Optional()]
    )
    activity_type = SelectField(
        "Activity type",
        choices=[(item.value, item.label) for item in ActivityType],
        validators=[InputRequired()],
    )
    occurred_at = DateTimeLocalField(
        "Occurred at",
        validators=[InputRequired()],
        format="%Y-%m-%dT%H:%M",
        default=datetime.now,
    )
    direction = SelectField(
        "Direction",
        choices=[(item.value, item.label) for item in ActivityDirection],
        validators=[InputRequired()],
    )
    subject = StringField("Subject", validators=[Optional(), Length(max=300)])
    summary = TextAreaField("Summary", validators=[Optional()])
    outcome = TextAreaField("Outcome", validators=[Optional()])
    follow_up_needed = BooleanField("Follow-up needed")
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save activity")

    def validate(self, extra_validators=None) -> bool:
        """Require at least one selected related entity."""
        valid = super().validate(extra_validators)
        if not any(
            (
                self.organization_id.data,
                self.contact_id.data,
                self.job_posting_id.data,
                self.application_id.data,
            )
        ):
            self.organization_id.errors.append(
                "Select at least one related entity."
            )
            return False
        return valid


class ActivityFilterForm(FlaskForm):
    """Date fields reused by the activity list filters."""

    class Meta:
        csrf = False

    date_from = DateField("From", validators=[Optional()])
    date_to = DateField("To", validators=[Optional()])


class DeleteActivityForm(FlaskForm):
    """CSRF-protected activity deletion confirmation."""

    submit = SubmitField("Delete activity")
