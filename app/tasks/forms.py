"""Forms for task management."""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import InputRequired, Length, Optional, ValidationError

from app.activities.forms import optional_int
from app.utils.enums import TaskPriority, TaskStatus, TaskType


class TaskForm(FlaskForm):
    """Create or update a task."""

    organization_id = SelectField("Organization", coerce=optional_int, validators=[Optional()])
    contact_id = SelectField("Contact", coerce=optional_int, validators=[Optional()])
    job_posting_id = SelectField("Job posting", coerce=optional_int, validators=[Optional()])
    application_id = SelectField("Application", coerce=optional_int, validators=[Optional()])
    title = StringField("Title", validators=[InputRequired(), Length(max=300)])
    description = TextAreaField("Description", validators=[Optional()])
    task_type = SelectField("Task type", choices=[(x.value, x.label) for x in TaskType], validators=[InputRequired()])
    priority = SelectField("Priority", choices=[(x.value, x.label) for x in TaskPriority], default=TaskPriority.MEDIUM.value, validators=[InputRequired()])
    status = SelectField("Status", choices=[(x.value, x.label) for x in TaskStatus], default=TaskStatus.OPEN.value, validators=[InputRequired()])
    due_date = DateField("Due date", validators=[Optional()])
    due_time = TimeField("Due time", validators=[Optional()])
    submit = SubmitField("Save task")

    def validate_due_time(self, field: TimeField) -> None:
        if field.data is not None and self.due_date.data is None:
            raise ValidationError("A due date is required when a due time is set.")


class TaskFilterForm(FlaskForm):
    class Meta:
        csrf = False
    due_from = DateField("Due from", validators=[Optional()])
    due_to = DateField("Due to", validators=[Optional()])


class TaskActionForm(FlaskForm):
    submit = SubmitField("Confirm")
