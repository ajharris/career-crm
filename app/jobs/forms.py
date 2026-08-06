"""Forms used by job posting management views."""

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DateTimeLocalField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    NumberRange,
    Optional,
    URL,
    ValidationError,
)

from app.utils.enums import EmploymentType, JobSource, JobStatus, WorkMode


def _choices(enum_class: type, empty_label: str | None = None) -> list[tuple[str, str]]:
    choices = [(item.value, item.label) for item in enum_class]
    return [('', empty_label)] + choices if empty_label else choices


class JobPostingForm(FlaskForm):
    """Create or update a job posting."""

    organization_id = SelectField(
        "Organization", coerce=int, validators=[InputRequired()]
    )
    title = StringField("Title", validators=[InputRequired(), Length(max=250)])
    department = StringField("Department", validators=[Optional(), Length(max=200)])
    location = StringField("Location", validators=[Optional(), Length(max=200)])
    employment_type = SelectField(
        "Employment type",
        choices=_choices(EmploymentType, "Select a type"),
        validators=[Optional()],
    )
    work_mode = SelectField(
        "Work mode",
        choices=_choices(WorkMode, "Select a mode"),
        validators=[Optional()],
    )
    salary_min = DecimalField(
        "Minimum salary", validators=[Optional(), NumberRange(min=0)], places=2
    )
    salary_max = DecimalField(
        "Maximum salary", validators=[Optional(), NumberRange(min=0)], places=2
    )
    salary_currency = SelectField(
        "Currency",
        choices=[
            ("", "Select currency"),
            ("CAD", "CAD"),
            ("USD", "USD"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
        ],
        validators=[Optional()],
    )
    posting_url = StringField(
        "Posting URL", validators=[Optional(), URL(), Length(max=1000)]
    )
    source = SelectField(
        "Source",
        choices=_choices(JobSource, "Select a source"),
        validators=[Optional()],
    )
    date_posted = DateField("Date posted", validators=[Optional()])
    closing_date = DateField("Closing date", validators=[Optional()])
    discovered_at = DateTimeLocalField(
        "Date discovered", validators=[Optional()], format="%Y-%m-%dT%H:%M"
    )
    priority = IntegerField(
        "Priority", validators=[InputRequired(), NumberRange(min=1, max=5)], default=3
    )
    status = SelectField(
        "Status", choices=_choices(JobStatus), default=JobStatus.DISCOVERED.value
    )
    description = TextAreaField("Description", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save job posting")

    def validate_salary_max(self, field: DecimalField) -> None:
        if self.salary_min.data is not None and field.data is not None:
            if self.salary_min.data > field.data:
                raise ValidationError(
                    "Maximum salary must be at least the minimum salary."
                )

    def validate_closing_date(self, field: DateField) -> None:
        if self.date_posted.data is not None and field.data is not None:
            if field.data < self.date_posted.data:
                raise ValidationError("Closing date cannot precede posting date.")


class DeleteJobPostingForm(FlaskForm):
    """CSRF-protected job deletion confirmation."""

    submit = SubmitField("Delete job posting")
