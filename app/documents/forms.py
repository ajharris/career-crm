"""Document forms."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional

ALLOWED = ("pdf", "doc", "docx", "txt", "odt", "png", "jpg", "jpeg")


class DocumentForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired(), Length(max=200)])
    document_type = SelectField(
        "Type",
        choices=[
            ("resume", "Résumé"),
            ("cover_letter", "Cover letter"),
            ("certificate", "Certificate"),
            ("portfolio", "Portfolio"),
        ],
    )
    description = TextAreaField("Description", validators=[Optional()])
    file = FileField(
        "File",
        validators=[FileRequired(), FileAllowed(ALLOWED, "Unsupported file type.")],
    )
    notes = TextAreaField("Version notes", validators=[Optional()])
    submit = SubmitField("Upload")


class VersionForm(FlaskForm):
    file = FileField(
        "New version",
        validators=[FileRequired(), FileAllowed(ALLOWED, "Unsupported file type.")],
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Add version")


class AttachForm(FlaskForm):
    application_id = SelectField(
        "Application", coerce=int, validators=[InputRequired()]
    )
    purpose = StringField("Purpose", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Attach latest version")
