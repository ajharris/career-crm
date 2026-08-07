"""HTTP routes for organization management."""

from flask import flash, redirect, render_template, request, url_for

from app.auth.permissions import require_shared_editor
from app.organizations import bp
from app.organizations.forms import DeleteOrganizationForm, OrganizationForm
from app.organizations.services import (
    SORT_COLUMNS,
    DuplicateOrganizationError,
    OrganizationValues,
    create_organization,
    delete_organization,
    get_organization,
    list_organizations,
    update_organization,
)


@bp.get("")
def index() -> str:
    """List organizations with search, sorting, and pagination."""
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "name")
    direction = request.args.get("direction", "asc")
    sort = sort if sort in SORT_COLUMNS else "name"
    direction = direction if direction in {"asc", "desc"} else "asc"
    page = request.args.get("page", 1, type=int) or 1
    pagination = list_organizations(
        search=search, sort=sort, direction=direction, page=page
    )
    return render_template(
        "organizations/index.html",
        pagination=pagination,
        search=search,
        sort=sort,
        direction=direction,
    )


@bp.get("/<int:organization_id>")
def detail(organization_id: int) -> str:
    """Show one organization."""
    from app.activities.services import recent_activities
    from app.contacts.services import contacts_for_organization
    from app.jobs.services import active_jobs_for_organization
    from app.tasks.services import context_tasks

    organization = get_organization(organization_id)
    return render_template(
        "organizations/detail.html",
        organization=organization,
        contacts=contacts_for_organization(organization.id),
        active_jobs=active_jobs_for_organization(organization.id),
        recent_activities=recent_activities(organization_id=organization.id),
        active_tasks=context_tasks(organization_id=organization.id),
    )


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    """Create an organization from validated form data."""
    form = OrganizationForm()
    if form.validate_on_submit():
        try:
            organization = create_organization(**_form_values(form))
        except DuplicateOrganizationError as error:
            form.name.errors.append(str(error))
        else:
            flash("Organization created successfully.", "success")
            return redirect(
                url_for("organizations.detail", organization_id=organization.id)
            )
    return render_template(
        "organizations/form.html", form=form, page_title="New organization"
    )


@bp.route("/<int:organization_id>/edit", methods=["GET", "POST"])
def edit(organization_id: int) -> str:
    """Edit an existing organization."""
    organization = get_organization(organization_id)
    require_shared_editor(organization)
    form = OrganizationForm(obj=organization)
    if form.validate_on_submit():
        try:
            update_organization(organization, **_form_values(form))
        except DuplicateOrganizationError as error:
            form.name.errors.append(str(error))
        else:
            flash("Organization updated successfully.", "success")
            return redirect(
                url_for("organizations.detail", organization_id=organization.id)
            )
    return render_template(
        "organizations/form.html",
        form=form,
        organization=organization,
        page_title="Edit organization",
    )


@bp.route("/<int:organization_id>/delete", methods=["GET", "POST"])
def delete(organization_id: int) -> str:
    """Confirm and delete an organization."""
    organization = get_organization(organization_id)
    require_shared_editor(organization)
    form = DeleteOrganizationForm()
    if form.validate_on_submit():
        delete_organization(organization)
        flash("Organization deleted successfully.", "success")
        return redirect(url_for("organizations.index"))
    return render_template(
        "organizations/delete.html", organization=organization, form=form
    )


def _form_values(form: OrganizationForm) -> OrganizationValues:
    """Extract the model fields accepted by the service layer."""
    return {
        "name": form.name.data,
        "organization_type": form.organization_type.data,
        "website": form.website.data,
        "location": form.location.data,
        "priority": form.priority.data,
        "notes": form.notes.data,
    }
