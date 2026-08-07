"""HTTP routes for activity management."""

from flask import flash, redirect, render_template, request, url_for

from app.activities import bp
from app.activities.forms import ActivityFilterForm, ActivityForm, DeleteActivityForm
from app.activities.services import (
    SORT_COLUMNS,
    ActivityValues,
    create_activity,
    delete_activity,
    entity_choices,
    get_activity,
    list_activities,
    update_activity,
)
from app.utils.enums import ActivityDirection, ActivityType


@bp.get("")
def index() -> str:
    """Render the searchable and filterable activity timeline."""
    filter_form = ActivityFilterForm(request.args)
    filters = _query_options(filter_form)
    return render_template(
        "activities/index.html",
        pagination=list_activities(**filters),
        activity_types=ActivityType,
        directions=ActivityDirection,
        filter_form=filter_form,
        **entity_choices(),
        **filters,
    )


@bp.get("/<int:activity_id>")
def detail(activity_id: int) -> str:
    """Show one activity."""
    return render_template("activities/detail.html", activity=get_activity(activity_id))


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    """Create an activity from validated form data."""
    form = ActivityForm()
    _set_entity_choices(form)
    if request.method == "GET":
        _apply_context_defaults(form)
    if form.validate_on_submit():
        activity = create_activity(**_form_values(form))
        flash("Activity created successfully.", "success")
        return redirect(url_for("activities.detail", activity_id=activity.id))
    return render_template("activities/form.html", form=form, page_title="New activity")


@bp.route("/<int:activity_id>/edit", methods=["GET", "POST"])
def edit(activity_id: int) -> str:
    """Edit an existing activity."""
    activity = get_activity(activity_id)
    form = ActivityForm(obj=activity)
    _set_entity_choices(form)
    if form.validate_on_submit():
        update_activity(activity, **_form_values(form))
        flash("Activity updated successfully.", "success")
        return redirect(url_for("activities.detail", activity_id=activity.id))
    return render_template(
        "activities/form.html",
        form=form,
        activity=activity,
        page_title="Edit activity",
    )


@bp.route("/<int:activity_id>/delete", methods=["GET", "POST"])
def delete(activity_id: int) -> str:
    """Confirm and delete an activity."""
    activity = get_activity(activity_id)
    form = DeleteActivityForm()
    if form.validate_on_submit():
        delete_activity(activity)
        flash("Activity deleted successfully.", "success")
        return redirect(url_for("activities.index"))
    return render_template("activities/delete.html", activity=activity, form=form)


def _set_entity_choices(form: ActivityForm) -> None:
    choices = entity_choices()
    form.organization_id.choices = [("", "No organization")] + choices["organizations"]
    form.contact_id.choices = [("", "No contact")] + choices["contacts"]
    form.job_posting_id.choices = [("", "No job posting")] + choices["jobs"]
    form.application_id.choices = [("", "No application")] + choices["applications"]


def _apply_context_defaults(form: ActivityForm) -> None:
    fields = (
        "organization_id",
        "contact_id",
        "job_posting_id",
        "application_id",
    )
    for field_name in fields:
        requested_id = request.args.get(field_name, type=int)
        field = getattr(form, field_name)
        valid_ids = {choice[0] for choice in field.choices if choice[0] != ""}
        if requested_id in valid_ids:
            field.data = requested_id


def _query_options(form: ActivityFilterForm) -> dict:
    sort = request.args.get("sort", "occurred_at")
    direction = request.args.get("sort_direction", "desc")
    dates_are_valid = form.validate()
    return {
        "search": request.args.get("q", "").strip(),
        "activity_type": request.args.get("activity_type", "").strip(),
        "direction": request.args.get("direction", "").strip(),
        "organization_id": request.args.get("organization_id", type=int),
        "contact_id": request.args.get("contact_id", type=int),
        "job_posting_id": request.args.get("job_posting_id", type=int),
        "application_id": request.args.get("application_id", type=int),
        "date_from": form.date_from.data if dates_are_valid else None,
        "date_to": form.date_to.data if dates_are_valid else None,
        "sort": sort if sort in SORT_COLUMNS else "occurred_at",
        "sort_direction": direction if direction in {"asc", "desc"} else "desc",
        "page": request.args.get("page", 1, type=int) or 1,
    }


def _form_values(form: ActivityForm) -> ActivityValues:
    """Extract model fields accepted by the service layer."""
    return {
        field: getattr(form, field).data for field in ActivityValues.__annotations__
    }
