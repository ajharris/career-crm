"""Forms for authentication and profile management."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


def _strip(value: str | None) -> str | None:
    return value.strip() if value else value


def _normalize_email(value: str | None) -> str | None:
    return value.strip().lower() if value else value


name_validators = [DataRequired(), Length(max=100)]
email_validators = [DataRequired(), Email(), Length(max=255)]
password_validators = [
    DataRequired(),
    Length(min=8, message="Password must be at least 8 characters long."),
]


class RegistrationForm(FlaskForm):
    first_name = StringField("First Name", validators=name_validators, filters=[_strip])
    last_name = StringField("Last Name", validators=name_validators, filters=[_strip])
    email = EmailField("Email", validators=email_validators, filters=[_normalize_email])
    password = PasswordField("Password", validators=password_validators)
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=email_validators, filters=[_normalize_email])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=name_validators, filters=[_strip])
    last_name = StringField("Last Name", validators=name_validators, filters=[_strip])
    email = EmailField("Email", validators=email_validators, filters=[_normalize_email])
    submit = SubmitField("Save Profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=password_validators)
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Update Password")


class LogoutForm(FlaskForm):
    submit = SubmitField("Log Out")
