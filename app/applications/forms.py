"""Forms used by application management views."""

from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    DecimalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    Email,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    URL,
    ValidationError,
)

from app.utils.enums import ApplicationStatus


class ApplicationForm(FlaskForm):
    """Create or update an application."""

    job_posting_id = SelectField(
        "Job posting", coerce=int, validators=[InputRequired()]
    )
    application_date = DateField("Application date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[(item.value, item.label) for item in ApplicationStatus],
        default=ApplicationStatus.PLANNED.value,
    )
    source = StringField("Source", validators=[Optional(), Length(max=100)])
    resume_version = StringField(
        "Résumé link",
        validators=[Optional(), URL(), Length(max=1000)],
        description="Link to the résumé in Google Docs or another document service.",
    )
    cover_letter_version = StringField(
        "Cover letter link",
        validators=[Optional(), URL(), Length(max=1000)],
        description=(
            "Link to the cover letter in Google Docs or another document service."
        ),
    )
    recruiter_name = StringField(
        "Recruiter name", validators=[Optional(), Length(max=200)]
    )
    recruiter_email = StringField(
        "Recruiter email", validators=[Optional(), Email(), Length(max=320)]
    )
    salary_requested = DecimalField(
        "Salary requested",
        validators=[Optional(), NumberRange(min=Decimal("0.01"))],
        places=2,
    )
    interview_date = DateTimeLocalField(
        "Interview date", validators=[Optional()], format="%Y-%m-%dT%H:%M"
    )
    interview_location = StringField(
        "Interview location", validators=[Optional(), Length(max=300)]
    )
    rejection_reason = TextAreaField("Rejection reason", validators=[Optional()])
    offer_salary = DecimalField(
        "Offer salary",
        validators=[Optional(), NumberRange(min=Decimal("0.01"))],
        places=2,
    )
    accepted = BooleanField("Accepted")
    withdrawn = BooleanField("Withdrawn")
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save application")

    def validate_interview_date(self, field: DateTimeLocalField) -> None:
        if self.application_date.data is not None and field.data is not None:
            if field.data.date() < self.application_date.data:
                raise ValidationError(
                    "Interview date cannot precede application date."
                )


class DeleteApplicationForm(FlaskForm):
    """CSRF-protected application deletion confirmation."""

    submit = SubmitField("Delete application")
