"""Contact model, relationship, service, and route tests."""

from datetime import datetime

import pytest
from flask.testing import FlaskClient

from app.contacts.services import (
    create_contact,
    delete_contact,
    list_contacts,
    update_contact,
)
from app.extensions import db
from app.models.contact import Contact
from app.models.organization import Organization
from app.organizations.services import create_organization
from app.utils.enums import OrganizationType, RelationshipStatus


def make_organization(name: str = "Toronto General") -> Organization:
    """Create an organization used by contact tests."""
    return create_organization(
        name=name,
        organization_type=OrganizationType.HOSPITAL.value,
        location="Toronto",
        priority=3,
    )


def contact_data(organization_id: int, first_name: str = "Alex") -> dict:
    """Return valid form and service data."""
    return {
        "organization_id": organization_id,
        "first_name": first_name,
        "last_name": "Morgan",
        "title": "Hiring Manager",
        "department": "Engineering",
        "email": f"{first_name.lower()}@example.org",
        "phone": "+1 416 555 0100",
        "linkedin_url": "https://www.linkedin.com/in/example",
        "profile_url": "https://example.org/team/alex-morgan",
        "resume_url": "https://docs.google.com/document/d/contact-resume",
        "relationship_status": RelationshipStatus.CONTACTED.value,
        "last_contacted_at": "2026-08-01T09:30",
        "notes": "Met at a conference",
    }


def service_data(organization_id: int, first_name: str = "Alex") -> dict:
    """Return contact data with service-native date values."""
    values = contact_data(organization_id, first_name)
    values["last_contacted_at"] = datetime(2026, 8, 1, 9, 30)
    return values


def test_contact_model_and_full_name(app) -> None:
    organization = make_organization()
    contact = Contact(
        organization_id=organization.id,
        first_name="  Alex ",
        last_name=" Morgan  ",
    )
    db.session.add(contact)
    db.session.commit()

    assert contact.full_name == "Alex Morgan"
    assert contact.organization is organization
    assert contact in organization.contacts
    assert contact.created_at is not None


@pytest.mark.parametrize("field", ["first_name", "last_name"])
def test_contact_requires_both_names(app, field: str) -> None:
    values = {"first_name": "Alex", "last_name": "Morgan"}
    values[field] = "   "

    with pytest.raises(ValueError, match="is required"):
        Contact(organization_id=1, **values)


def test_deleting_organization_cascades_to_contacts(app) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))
    contact_id = contact.id

    db.session.delete(organization)
    db.session.commit()

    assert db.session.get(Contact, contact_id) is None


def test_create_contact_service(app) -> None:
    organization = make_organization()

    contact = create_contact(**service_data(organization.id))

    assert db.session.get(Contact, contact.id) is contact
    assert contact.organization_id == organization.id
    assert contact.relationship_status is RelationshipStatus.CONTACTED


def test_update_contact_service(app) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))

    updated = update_contact(contact, first_name="Jordan", title="Recruiter")

    assert updated.first_name == "Jordan"
    assert updated.title == "Recruiter"


def test_delete_contact_service(app) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))
    contact_id = contact.id

    delete_contact(contact)

    assert db.session.get(Contact, contact_id) is None


def test_list_route(authenticated_client: FlaskClient) -> None:
    response = authenticated_client.get("/contacts")

    assert response.status_code == 200
    assert b"New Contact" in response.data


def test_create_and_detail_routes(authenticated_client: FlaskClient) -> None:
    organization = make_organization()

    response = authenticated_client.post(
        "/contacts/new",
        data=contact_data(organization.id),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Contact created successfully." in response.data
    assert b"Alex Morgan" in response.data
    assert b"Contacted" in response.data
    assert b"Created" in response.data
    assert b"Updated" in response.data
    assert b'href="https://example.org/team/alex-morgan"' in response.data
    assert b'href="https://docs.google.com/document/d/contact-resume"' in response.data
    assert b"Open r\xc3\xa9sum\xc3\xa9 in Google Drive" in response.data


def test_create_and_add_another_returns_to_preselected_form(
    authenticated_client: FlaskClient,
) -> None:
    organization = make_organization()
    values = contact_data(organization.id)
    values["action"] = "save_and_new"

    response = authenticated_client.post("/contacts/new", data=values)

    assert response.status_code == 302
    assert response.location.endswith(
        f"/contacts/new?organization_id={organization.id}"
    )
    assert db.session.scalar(db.select(db.func.count(Contact.id))) == 1

    next_form = authenticated_client.get(response.location)
    assert b"Contact created successfully." in next_form.data
    assert b"Save and add another" in next_form.data
    assert f'<option selected value="{organization.id}"'.encode() in next_form.data
    assert b'value="Alex"' not in next_form.data


def test_add_another_action_is_only_shown_when_creating(
    authenticated_client: FlaskClient,
) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))

    create_response = authenticated_client.get("/contacts/new")
    edit_response = authenticated_client.get(f"/contacts/{contact.id}/edit")

    assert b"Save and add another" in create_response.data
    assert b"Save and add another" not in edit_response.data


def test_create_route_validates_fields(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    values = contact_data(organization.id)
    values.update(
        first_name="",
        email="invalid",
        linkedin_url="invalid",
        profile_url="invalid",
        resume_url="invalid",
    )

    response = authenticated_client.post("/contacts/new", data=values)

    assert response.status_code == 200
    assert b"This field is required." in response.data
    assert b"Invalid email address." in response.data
    assert b"Invalid URL." in response.data
    assert response.data.count(b"Invalid URL.") == 3


def test_new_contact_preselects_organization(authenticated_client: FlaskClient) -> None:
    organization = make_organization()

    response = authenticated_client.get(
        f"/contacts/new?organization_id={organization.id}"
    )

    selected = f'<option selected value="{organization.id}"'.encode()
    assert selected in response.data


def test_new_contact_defaults_relationship_status_to_new(
    authenticated_client: FlaskClient,
) -> None:
    response = authenticated_client.get("/contacts/new")

    assert b'<option selected value="new">New</option>' in response.data


def test_edit_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))
    values = contact_data(organization.id, "Jordan")
    values["last_name"] = "Lee"

    response = authenticated_client.post(
        f"/contacts/{contact.id}/edit", data=values, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Contact updated successfully." in response.data
    assert contact.full_name == "Jordan Lee"


def test_delete_requires_confirmation(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))

    response = authenticated_client.get(f"/contacts/{contact.id}/delete")

    assert response.status_code == 200
    assert b"Are you sure" in response.data
    assert db.session.get(Contact, contact.id) is contact


def test_delete_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    contact = create_contact(**service_data(organization.id))
    contact_id = contact.id

    response = authenticated_client.post(
        f"/contacts/{contact_id}/delete", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Contact deleted successfully." in response.data
    assert db.session.get(Contact, contact_id) is None


@pytest.mark.parametrize(
    "query", ["alex", "MORGAN", "toronto general", "hiring", "example.org"]
)
def test_search_is_case_insensitive(
    authenticated_client: FlaskClient, query: str
) -> None:
    organization = make_organization()
    create_contact(**service_data(organization.id))

    response = authenticated_client.get("/contacts", query_string={"q": query})

    assert b"Alex Morgan" in response.data


def test_filters_by_organization_and_title(authenticated_client: FlaskClient) -> None:
    first = make_organization("First Organization")
    second = make_organization("Second Organization")
    create_contact(**service_data(first.id, "Alex"))
    second_values = service_data(second.id, "Bailey")
    second_values["title"] = "Recruiter"
    create_contact(**second_values)

    by_organization = authenticated_client.get(
        "/contacts", query_string={"organization_id": second.id}
    )
    by_title = authenticated_client.get(
        "/contacts", query_string={"title": "Recruiter"}
    )

    assert b"Bailey Morgan" in by_organization.data
    assert b"Alex Morgan" not in by_organization.data
    assert b"Bailey Morgan" in by_title.data
    assert b"Alex Morgan" not in by_title.data


def test_search_and_filters_work_together(authenticated_client: FlaskClient) -> None:
    first = make_organization("First Organization")
    second = make_organization("Second Organization")
    create_contact(**service_data(first.id, "Alex"))
    create_contact(**service_data(second.id, "Bailey"))

    response = authenticated_client.get(
        "/contacts",
        query_string={"q": "bailey", "organization_id": second.id},
    )

    assert b"Bailey Morgan" in response.data
    assert b"Alex Morgan" not in response.data


def test_contact_sorting_options(app) -> None:
    alpha_organization = make_organization("Alpha Organization")
    zulu_organization = make_organization("Zulu Organization")
    first_values = service_data(zulu_organization.id, "First")
    first_values.update(
        last_name="Zulu",
        last_contacted_at=datetime(2026, 1, 1, 9, 0),
    )
    second_values = service_data(alpha_organization.id, "Second")
    second_values.update(
        last_name="Alpha",
        last_contacted_at=datetime(2026, 2, 1, 9, 0),
    )
    first = create_contact(**first_values)
    second = create_contact(**second_values)
    first.created_at = datetime(2026, 1, 1)
    second.created_at = datetime(2026, 2, 1)
    db.session.commit()

    assert [item.id for item in list_contacts(sort="last_name").items] == [
        second.id,
        first.id,
    ]
    assert [item.id for item in list_contacts(sort="organization").items] == [
        second.id,
        first.id,
    ]
    assert [item.id for item in list_contacts(sort="created_at").items] == [
        first.id,
        second.id,
    ]
    assert [
        item.id
        for item in list_contacts(sort="last_contacted_at", direction="desc").items
    ] == [second.id, first.id]


def test_sorting_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    first = create_contact(**service_data(organization.id, "First"))
    second = create_contact(**service_data(organization.id, "Second"))
    update_contact(first, last_name="Alpha")
    update_contact(second, last_name="Zulu")

    response = authenticated_client.get("/contacts?sort=last_name&direction=desc")

    assert response.data.index(b"Second Zulu") < response.data.index(b"First Alpha")


def test_pagination_displays_25_contacts(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    for number in range(27):
        values = service_data(organization.id, f"Person{number:02d}")
        values["email"] = f"person{number:02d}@example.org"
        create_contact(**values)

    pagination = list_contacts(page=1)
    second_page = authenticated_client.get("/contacts?page=2")

    assert len(pagination.items) == 25
    assert pagination.total == 27
    assert b"Person25 Morgan" in second_page.data


def test_organization_detail_lists_contacts(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    create_contact(**service_data(organization.id))

    response = authenticated_client.get(f"/organizations/{organization.id}")

    assert b"Add Contact" in response.data
    assert b"Alex Morgan" in response.data
