"""Forms used by organization management views."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, NumberRange, Optional, URL

from app.utils.enums import OrganizationType


class OrganizationForm(FlaskForm):
    """Create or update an organization."""

    name = StringField(
        "Name",
        validators=[InputRequired(), Length(max=200)],
        render_kw={"autofocus": True},
    )
    organization_type = SelectField(
        "Organization type",
        choices=[("", "Select a type")] + [
            (item.value, item.label) for item in OrganizationType
        ],
        validators=[Optional()],
    )
    website = StringField(
        "Website",
        validators=[Optional(), URL(), Length(max=500)],
        description="Include http:// or https://",
    )
    location = StringField("Location", validators=[Optional(), Length(max=200)])
    priority = IntegerField(
        "Priority",
        validators=[InputRequired(), NumberRange(min=1, max=5)],
        default=3,
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save organization")


class DeleteOrganizationForm(FlaskForm):
    """CSRF-protected organization deletion confirmation."""

    submit = SubmitField("Delete organization")
