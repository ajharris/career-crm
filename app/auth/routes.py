"""HTTP routes for authentication and account profiles."""

from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp
from app.auth.forms import (
    ChangePasswordForm,
    LoginForm,
    LogoutForm,
    ProfileForm,
    RegistrationForm,
)
from app.auth.services import (
    EmailAlreadyRegisteredError,
    InvalidCurrentPasswordError,
    authenticate_user,
    change_password,
    create_user,
    update_profile,
)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Create and sign in a new account."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = create_user(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password=form.password.data,
            )
        except EmailAlreadyRegisteredError as exc:
            form.email.errors = (*form.email.errors, str(exc))
        else:
            login_user(user)
            flash("Welcome to Career CRM!", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an account and honor only safe local redirects."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.email.data, form.password.data)
        if user is None:
            flash("Invalid email or password.", "danger")
        else:
            login_user(user, remember=form.remember.data)
            destination = request.args.get("next", "")
            if not _is_safe_local_path(destination):
                destination = url_for("dashboard.index")
            return redirect(destination)
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    """End the current authenticated session."""
    form = LogoutForm()
    if form.validate_on_submit():
        logout_user()
        flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@bp.get("/profile")
@login_required
def profile():
    """Display the current user's non-sensitive account details."""
    return render_template("auth/profile.html")


@bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit the current user's name and email address."""
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            update_profile(
                current_user,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
            )
        except EmailAlreadyRegisteredError as exc:
            form.email.errors = (*form.email.errors, str(exc))
        else:
            flash("Your profile has been updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/edit_profile.html", form=form)


@bp.route("/password/change", methods=["GET", "POST"])
@login_required
def change_password_view():
    """Verify and replace the current user's password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            change_password(
                current_user, form.current_password.data, form.new_password.data
            )
        except InvalidCurrentPasswordError as exc:
            form.current_password.errors = (*form.current_password.errors, str(exc))
        else:
            flash("Your password has been updated.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", form=form)


def _is_safe_local_path(target: str) -> bool:
    parts = urlsplit(target)
    return (
        bool(target)
        and not parts.scheme
        and not parts.netloc
        and target.startswith("/")
    )
