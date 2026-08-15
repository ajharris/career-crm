"""HTTP routes for application management."""

from flask import flash, redirect, render_template, request, url_for

from app.applications import bp
from app.applications.forms import ApplicationForm, DeleteApplicationForm
from app.applications.services import (
    SORT_COLUMNS,
    ApplicationValues,
    DuplicateApplicationError,
    applied_year_choices,
    available_job_choices,
    create_application,
    delete_application,
    get_application,
    list_applications,
    organization_choices,
    update_application,
)
from app.models.application import Application
from app.utils.enums import ApplicationStatus


@bp.get("")
def index() -> str:
    """List applications with search, filters, sorting, and pagination."""
    filters = _query_options()
    return render_template(
        "applications/index.html",
        pagination=list_applications(**filters),
        statuses=ApplicationStatus,
        organizations=organization_choices(),
        years=applied_year_choices(),
        **filters,
    )


@bp.get("/<int:application_id>")
def detail(application_id: int) -> str:
    """Show one application."""
    from app.activities.services import recent_activities
    from app.tasks.services import context_tasks

    application = get_application(application_id)
    return render_template(
        "applications/detail.html",
        application=application,
        recent_activities=recent_activities(application_id=application.id),
        active_tasks=context_tasks(application_id=application.id),
        completed_tasks=context_tasks(application_id=application.id, completed=True),
    )


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    """Create an application from validated form data."""
    form = ApplicationForm()
    _set_job_choices(form)
    context_job = _context_job()
    if request.method == "GET":
        requested_job = request.args.get("job_posting_id", type=int)
        if requested_job in dict(form.job_posting_id.choices):
            form.job_posting_id.data = requested_job
    if form.validate_on_submit():
        try:
            application = create_application(**_form_values(form))
        except DuplicateApplicationError as error:
            form.job_posting_id.errors.append(str(error))
        else:
            flash("Application created successfully.", "success")
            if request.form.get("action") == "save_and_new":
                return redirect(url_for("applications.create"))
            return redirect(
                url_for("applications.detail", application_id=application.id)
            )
    return render_template(
        "applications/form.html",
        form=form,
        page_title="New application",
        context_job=context_job,
    )


@bp.route("/<int:application_id>/edit", methods=["GET", "POST"])
def edit(application_id: int) -> str:
    """Edit an existing application."""
    application = get_application(application_id)
    form = ApplicationForm(obj=application)
    _set_job_choices(form, application)
    if form.validate_on_submit():
        try:
            update_application(application, **_form_values(form))
        except DuplicateApplicationError as error:
            form.job_posting_id.errors.append(str(error))
        else:
            flash("Application updated successfully.", "success")
            return redirect(
                url_for("applications.detail", application_id=application.id)
            )
    return render_template(
        "applications/form.html",
        form=form,
        application=application,
        page_title="Edit application",
    )


@bp.route("/<int:application_id>/delete", methods=["GET", "POST"])
def delete(application_id: int) -> str:
    """Confirm and delete an application."""
    application = get_application(application_id)
    job_id = application.job_posting_id
    form = DeleteApplicationForm()
    if form.validate_on_submit():
        delete_application(application)
        flash("Application deleted successfully.", "success")
        return redirect(url_for("jobs.detail", job_id=job_id))
    return render_template(
        "applications/delete.html", application=application, form=form
    )


def _set_job_choices(
    form: ApplicationForm, application: Application | None = None
) -> None:
    form.job_posting_id.choices = available_job_choices(application)


def _context_job():
    job_id = request.args.get("job_posting_id", type=int)
    if job_id is None:
        return None
    from app.jobs.services import get_job_posting

    return get_job_posting(job_id)


def _query_options() -> dict:
    sort = request.args.get("sort", "updated_at")
    direction = request.args.get("direction", "desc")
    return {
        "search": request.args.get("q", "").strip(),
        "status": request.args.get("status", "").strip(),
        "organization_id": request.args.get("organization_id", type=int),
        "applied_year": request.args.get("applied_year", type=int),
        "accepted": _optional_bool(request.args.get("accepted", "")),
        "withdrawn": _optional_bool(request.args.get("withdrawn", "")),
        "sort": sort if sort in SORT_COLUMNS else "updated_at",
        "direction": direction if direction in {"asc", "desc"} else "desc",
        "page": request.args.get("page", 1, type=int) or 1,
    }


def _optional_bool(value: str) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _form_values(form: ApplicationForm) -> ApplicationValues:
    """Extract model fields accepted by the service layer."""
    return {
        field: getattr(form, field).data for field in ApplicationValues.__annotations__
    }
