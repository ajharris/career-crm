"""HTTP routes for task management."""

from flask import flash, redirect, render_template, request, url_for

from app.activities.services import entity_choices, get_activity
from app.tasks import bp
from app.tasks.forms import TaskActionForm, TaskFilterForm, TaskForm
from app.tasks.services import (
    SORT_COLUMNS,
    TaskValues,
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    reopen_task,
    update_task,
)
from app.utils.enums import TaskPriority, TaskStatus, TaskType


@bp.get("")
def index():
    form = TaskFilterForm(request.args)
    valid = form.validate()
    options = {
        "search": request.args.get("q", ""),
        "status": request.args.get("status", ""),
        "priority": request.args.get("priority", ""),
        "task_type": request.args.get("task_type", ""),
        "organization_id": request.args.get("organization_id", type=int),
        "contact_id": request.args.get("contact_id", type=int),
        "due_from": form.due_from.data if valid else None,
        "due_to": form.due_to.data if valid else None,
        "overdue": request.args.get("overdue") == "1",
        "completed_only": request.args.get("completed") == "1",
        "sort": request.args.get("sort", "actionable"),
        "sort_direction": request.args.get("sort_direction", "asc"),
        "page": request.args.get("page", 1, type=int) or 1,
    }
    if options["sort"] not in {*SORT_COLUMNS, "priority", "actionable"}:
        options["sort"] = "actionable"
    return render_template(
        "tasks/index.html",
        pagination=list_tasks(**options),
        filter_form=form,
        task_types=TaskType,
        priorities=TaskPriority,
        statuses=TaskStatus,
        **entity_choices(),
        **options,
    )


@bp.get("/<int:task_id>")
def detail(task_id):
    return render_template(
        "tasks/detail.html", task=get_task(task_id), action_form=TaskActionForm()
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = TaskForm()
    _choices(form)
    if request.method == "GET":
        _defaults(form)
    if form.validate_on_submit():
        task = create_task(**_values(form))
        flash("Task created successfully.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))
    return render_template("tasks/form.html", form=form, page_title="New task")


@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
def edit(task_id):
    task = get_task(task_id)
    form = TaskForm(obj=task)
    _choices(form)
    if form.validate_on_submit():
        update_task(task, **_values(form))
        flash("Task updated successfully.", "success")
        return redirect(url_for("tasks.detail", task_id=task.id))
    return render_template(
        "tasks/form.html", form=form, task=task, page_title="Edit task"
    )


@bp.route("/<int:task_id>/delete", methods=["GET", "POST"])
def delete(task_id):
    task = get_task(task_id)
    form = TaskActionForm()
    if form.validate_on_submit():
        delete_task(task)
        flash("Task deleted successfully.", "success")
        return redirect(url_for("tasks.index"))
    return render_template("tasks/delete.html", task=task, form=form)


@bp.post("/<int:task_id>/complete")
def complete(task_id):
    form = TaskActionForm()
    if form.validate_on_submit():
        complete_task(get_task(task_id))
        flash("Task completed successfully.", "success")
    return redirect(url_for("tasks.detail", task_id=task_id))


@bp.post("/<int:task_id>/reopen")
def reopen(task_id):
    form = TaskActionForm()
    if form.validate_on_submit():
        reopen_task(get_task(task_id))
        flash("Task reopened successfully.", "success")
    return redirect(url_for("tasks.detail", task_id=task_id))


def _choices(form):
    choices = entity_choices()
    for field, key, label in (
        (form.organization_id, "organizations", "organization"),
        (form.contact_id, "contacts", "contact"),
        (form.job_posting_id, "jobs", "job posting"),
        (form.application_id, "applications", "application"),
    ):
        field.choices = [("", f"No {label}")] + choices[key]


def _defaults(form):
    for name in ("organization_id", "contact_id", "job_posting_id", "application_id"):
        value = request.args.get(name, type=int)
        field = getattr(form, name)
        if value in {x[0] for x in field.choices}:
            field.data = value
    activity_id = request.args.get("activity_id", type=int)
    if activity_id:
        activity = get_activity(activity_id)
        for name in (
            "organization_id",
            "contact_id",
            "job_posting_id",
            "application_id",
        ):
            getattr(form, name).data = getattr(activity, name)
        form.task_type.data = TaskType.FOLLOW_UP.value
        form.title.data = (
            f"Follow up: {activity.subject or activity.activity_type.label}"
        )
        form.description.data = activity.summary or activity.outcome


def _values(form) -> TaskValues:
    return {name: getattr(form, name).data for name in TaskValues.__annotations__}
