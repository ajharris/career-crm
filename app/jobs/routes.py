"""HTTP routes for job posting management."""

from flask import flash, redirect, render_template, request, url_for

from app.jobs import bp
from app.jobs.forms import DeleteJobPostingForm, JobPostingForm
from app.jobs.services import (
    SORT_COLUMNS,
    JobPostingValues,
    create_job_posting,
    delete_job_posting,
    get_job_posting,
    list_job_postings,
    organization_choices,
    update_job_posting,
)
from app.utils.enums import EmploymentType, JobStatus, WorkMode


@bp.get("")
def index() -> str:
    """List job postings with search, filters, sorting, and pagination."""
    filters = _query_options()
    pagination = list_job_postings(**filters)
    return render_template(
        "jobs/index.html",
        pagination=pagination,
        organizations=organization_choices(),
        statuses=JobStatus,
        employment_types=EmploymentType,
        work_modes=WorkMode,
        **filters,
    )


@bp.get("/<int:job_id>")
def detail(job_id: int) -> str:
    """Show one job posting."""
    return render_template("jobs/detail.html", job=get_job_posting(job_id))


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    """Create a job posting from validated form data."""
    form = JobPostingForm()
    _set_organization_choices(form)
    if request.method == "GET":
        requested_organization = request.args.get("organization_id", type=int)
        if requested_organization in dict(form.organization_id.choices):
            form.organization_id.data = requested_organization
    if form.validate_on_submit():
        job = create_job_posting(**_form_values(form))
        flash("Job posting created successfully.", "success")
        return redirect(url_for("jobs.detail", job_id=job.id))
    return render_template("jobs/form.html", form=form, page_title="New job posting")


@bp.route("/<int:job_id>/edit", methods=["GET", "POST"])
def edit(job_id: int) -> str:
    """Edit an existing job posting."""
    job = get_job_posting(job_id)
    form = JobPostingForm(obj=job)
    _set_organization_choices(form)
    if form.validate_on_submit():
        update_job_posting(job, **_form_values(form))
        flash("Job posting updated successfully.", "success")
        return redirect(url_for("jobs.detail", job_id=job.id))
    return render_template(
        "jobs/form.html", form=form, job=job, page_title="Edit job posting"
    )


@bp.route("/<int:job_id>/delete", methods=["GET", "POST"])
def delete(job_id: int) -> str:
    """Confirm and delete a job posting."""
    job = get_job_posting(job_id)
    organization_id = job.organization_id
    form = DeleteJobPostingForm()
    if form.validate_on_submit():
        delete_job_posting(job)
        flash("Job posting deleted successfully.", "success")
        return redirect(
            url_for("organizations.detail", organization_id=organization_id)
        )
    return render_template("jobs/delete.html", job=job, form=form)


def _set_organization_choices(form: JobPostingForm) -> None:
    form.organization_id.choices = organization_choices()


def _query_options() -> dict:
    sort = request.args.get("sort", "created_at")
    direction = request.args.get("direction", "desc")
    return {
        "search": request.args.get("q", "").strip(),
        "organization_id": request.args.get("organization_id", type=int),
        "status": request.args.get("status", "").strip(),
        "employment_type": request.args.get("employment_type", "").strip(),
        "work_mode": request.args.get("work_mode", "").strip(),
        "priority": request.args.get("priority", type=int),
        "sort": sort if sort in SORT_COLUMNS else "created_at",
        "direction": direction if direction in {"asc", "desc"} else "desc",
        "page": request.args.get("page", 1, type=int) or 1,
    }


def _form_values(form: JobPostingForm) -> JobPostingValues:
    """Extract model fields accepted by the service layer."""
    return {
        field: getattr(form, field).data
        for field in JobPostingValues.__annotations__
    }
