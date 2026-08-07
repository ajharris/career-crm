"""HTTP routes for contact management."""

from flask import flash, redirect, render_template, request, url_for

from app.contacts import bp
from app.contacts.forms import ContactForm, DeleteContactForm
from app.contacts.services import (
    SORT_COLUMNS,
    ContactValues,
    create_contact,
    delete_contact,
    get_contact,
    list_contacts,
    organization_choices,
    title_choices,
    update_contact,
)


@bp.get("")
def index() -> str:
    """List contacts with search, filters, and pagination."""
    search = request.args.get("q", "").strip()
    organization_id = request.args.get("organization_id", type=int)
    title = request.args.get("title", "").strip()
    sort = request.args.get("sort", "last_name")
    direction = request.args.get("direction", "asc")
    sort = sort if sort in SORT_COLUMNS else "last_name"
    direction = direction if direction in {"asc", "desc"} else "asc"
    page = request.args.get("page", 1, type=int) or 1
    pagination = list_contacts(
        search=search,
        organization_id=organization_id,
        title=title,
        sort=sort,
        direction=direction,
        page=page,
    )
    return render_template(
        "contacts/index.html",
        pagination=pagination,
        search=search,
        selected_organization_id=organization_id,
        selected_title=title,
        sort=sort,
        direction=direction,
        organizations=organization_choices(),
        titles=title_choices(),
    )


@bp.get("/<int:contact_id>")
def detail(contact_id: int) -> str:
    """Show one contact."""
    from app.activities.services import recent_activities
    from app.tasks.services import context_tasks

    contact = get_contact(contact_id)
    return render_template(
        "contacts/detail.html",
        contact=contact,
        recent_activities=recent_activities(contact_id=contact.id),
        active_tasks=context_tasks(contact_id=contact.id),
    )


@bp.route("/new", methods=["GET", "POST"])
def create() -> str:
    """Create a contact from validated form data."""
    form = ContactForm()
    _set_organization_choices(form)
    if request.method == "GET":
        requested_organization = request.args.get("organization_id", type=int)
        if requested_organization in dict(form.organization_id.choices):
            form.organization_id.data = requested_organization
    if form.validate_on_submit():
        contact = create_contact(**_form_values(form))
        flash("Contact created successfully.", "success")
        return redirect(url_for("contacts.detail", contact_id=contact.id))
    return render_template("contacts/form.html", form=form, page_title="New contact")


@bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
def edit(contact_id: int) -> str:
    """Edit an existing contact."""
    contact = get_contact(contact_id)
    form = ContactForm(obj=contact)
    _set_organization_choices(form)
    if form.validate_on_submit():
        update_contact(contact, **_form_values(form))
        flash("Contact updated successfully.", "success")
        return redirect(url_for("contacts.detail", contact_id=contact.id))
    return render_template(
        "contacts/form.html", form=form, contact=contact, page_title="Edit contact"
    )


@bp.route("/<int:contact_id>/delete", methods=["GET", "POST"])
def delete(contact_id: int) -> str:
    """Confirm and delete a contact."""
    contact = get_contact(contact_id)
    organization_id = contact.organization_id
    form = DeleteContactForm()
    if form.validate_on_submit():
        delete_contact(contact)
        flash("Contact deleted successfully.", "success")
        return redirect(
            url_for("organizations.detail", organization_id=organization_id)
        )
    return render_template("contacts/delete.html", contact=contact, form=form)


def _set_organization_choices(form: ContactForm) -> None:
    form.organization_id.choices = organization_choices()


def _form_values(form: ContactForm) -> ContactValues:
    """Extract the model fields accepted by the service layer."""
    return {
        "organization_id": form.organization_id.data,
        "first_name": form.first_name.data,
        "last_name": form.last_name.data,
        "title": form.title.data,
        "department": form.department.data,
        "email": form.email.data,
        "phone": form.phone.data,
        "linkedin_url": form.linkedin_url.data,
        "notes": form.notes.data,
        "relationship_status": form.relationship_status.data,
        "last_contacted_at": form.last_contacted_at.data,
    }
