"""Forms used by contact management views."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import Email, InputRequired, Length, Optional, URL

from app.utils.enums import RelationshipStatus


class ContactForm(FlaskForm):
    """Create or update a contact."""

    organization_id = SelectField(
        "Organization", coerce=int, validators=[InputRequired()]
    )
    first_name = StringField(
        "First name",
        validators=[InputRequired(), Length(max=100)],
        render_kw={"autofocus": True},
    )
    last_name = StringField(
        "Last name", validators=[InputRequired(), Length(max=100)]
    )
    title = StringField("Title", validators=[Optional(), Length(max=200)])
    department = StringField("Department", validators=[Optional(), Length(max=200)])
    email = StringField(
        "Email", validators=[Optional(), Email(), Length(max=320)]
    )
    phone = StringField("Phone", validators=[Optional(), Length(max=50)])
    linkedin_url = StringField(
        "LinkedIn URL",
        validators=[Optional(), URL(), Length(max=500)],
        description="Include https://",
    )
    relationship_status = SelectField(
        "Relationship status",
        choices=[("", "Select a status")] + [
            (item.value, item.label) for item in RelationshipStatus
        ],
        validators=[Optional()],
    )
    last_contacted_at = DateTimeLocalField(
        "Last contacted", validators=[Optional()], format="%Y-%m-%dT%H:%M"
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save contact")


class DeleteContactForm(FlaskForm):
    """CSRF-protected contact deletion confirmation."""

    submit = SubmitField("Delete contact")
