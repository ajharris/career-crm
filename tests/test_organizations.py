"""Organization model, service, and route tests."""

from datetime import datetime

import pytest
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.organization import Organization
from app.organizations.services import (
    OrganizationValues,
    create_organization,
    delete_organization,
    list_organizations,
    update_organization,
)
from app.utils.enums import OrganizationType


def organization_data(
    name: str = "Toronto General",
    *,
    organization_type: str = OrganizationType.HOSPITAL.value,
    location: str = "Toronto",
    priority: int = 4,
) -> OrganizationValues:
    """Return valid form/service data."""
    return {
        "name": name,
        "organization_type": organization_type,
        "website": "https://example.org",
        "location": location,
        "priority": priority,
        "notes": "Potential employer",
    }


def test_organization_creation_sets_defaults_and_timestamps(app) -> None:
    organization = Organization(name="  Example Health  ", priority=3)
    db.session.add(organization)
    db.session.commit()

    assert organization.id is not None
    assert organization.name == "Example Health"
    assert isinstance(organization.created_at, datetime)
    assert isinstance(organization.updated_at, datetime)


def test_organization_name_is_unique(app) -> None:
    db.session.add(Organization(name="Unique Name", priority=3))
    db.session.commit()
    db.session.add(Organization(name="Unique Name", priority=3))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize("priority", [0, 6])
def test_organization_rejects_invalid_priority(app, priority: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        Organization(name="Invalid", priority=priority)


def test_organization_rejects_blank_name(app) -> None:
    with pytest.raises(ValueError, match="name is required"):
        Organization(name="   ", priority=3)


def test_create_organization_service(app) -> None:
    organization = create_organization(**organization_data())

    assert db.session.get(Organization, organization.id) is organization
    assert organization.organization_type is OrganizationType.HOSPITAL


def test_update_organization_service(app) -> None:
    organization = create_organization(**organization_data())

    updated = update_organization(organization, name="Updated Name", priority=5)

    assert updated.name == "Updated Name"
    assert updated.priority == 5


def test_delete_organization_service(app) -> None:
    organization = create_organization(**organization_data())
    organization_id = organization.id

    delete_organization(organization)

    assert db.session.get(Organization, organization_id) is None


def test_list_route(authenticated_client: FlaskClient) -> None:
    response = authenticated_client.get("/organizations")

    assert response.status_code == 200
    assert b"New Organization" in response.data


def test_detail_route(authenticated_client: FlaskClient) -> None:
    organization = create_organization(**organization_data())

    response = authenticated_client.get(f"/organizations/{organization.id}")

    assert response.status_code == 200
    assert b"Toronto General" in response.data
    assert b"Hospital" in response.data


def test_create_route(authenticated_client: FlaskClient) -> None:
    response = authenticated_client.post("/organizations/new", data=organization_data())

    assert response.status_code == 302
    assert response.location == "/organizations"

    response = authenticated_client.get(response.location)

    assert response.status_code == 200
    assert b"Organization created successfully." in response.data
    assert b"New Organization" in response.data
    assert db.session.scalar(db.select(Organization).filter_by(name="Toronto General"))


def test_create_route_displays_validation_errors(
    authenticated_client: FlaskClient,
) -> None:
    data = organization_data()
    data["name"] = ""
    data["website"] = "not-a-url"
    data["priority"] = 8

    response = authenticated_client.post("/organizations/new", data=data)

    assert response.status_code == 200
    assert b"This field is required." in response.data
    assert b"Invalid URL." in response.data
    assert b"Number must be between 1 and 5." in response.data


def test_edit_route(authenticated_client: FlaskClient) -> None:
    organization = create_organization(**organization_data())
    data = organization_data("New Organization Name")

    response = authenticated_client.post(
        f"/organizations/{organization.id}/edit",
        data=data,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Organization updated successfully." in response.data
    assert organization.name == "New Organization Name"


def test_delete_requires_confirmation(authenticated_client: FlaskClient) -> None:
    organization = create_organization(**organization_data())

    response = authenticated_client.get(f"/organizations/{organization.id}/delete")

    assert response.status_code == 200
    assert b"Are you sure" in response.data
    assert db.session.get(Organization, organization.id) is organization


def test_delete_route(authenticated_client: FlaskClient) -> None:
    organization = create_organization(**organization_data())
    organization_id = organization.id

    response = authenticated_client.post(
        f"/organizations/{organization_id}/delete", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Organization deleted successfully." in response.data
    assert db.session.get(Organization, organization_id) is None


def test_search_is_case_insensitive(authenticated_client: FlaskClient) -> None:
    create_organization(**organization_data("Alpha Hospital"))
    create_organization(
        **organization_data(
            "Beta Research",
            organization_type=OrganizationType.RESEARCH_INSTITUTE.value,
            location="Montreal",
        )
    )

    response = authenticated_client.get("/organizations?q=montREAL")

    assert b"Beta Research" in response.data
    assert b"Alpha Hospital" not in response.data

    type_response = authenticated_client.get("/organizations?q=Research+Institute")
    assert b"Beta Research" in type_response.data


def test_sorting_route(authenticated_client: FlaskClient) -> None:
    create_organization(**organization_data("Low", priority=1))
    create_organization(**organization_data("High", priority=5))

    response = authenticated_client.get("/organizations?sort=priority&direction=desc")

    assert response.data.index(b"High") < response.data.index(b"Low")


def test_sorting_by_priority_descending(app) -> None:
    create_organization(**organization_data("Low", priority=1))
    create_organization(**organization_data("High", priority=5))

    pagination = list_organizations(sort="priority", direction="desc")

    assert [item.name for item in pagination.items] == ["High", "Low"]


def test_pagination_displays_25_organizations(
    authenticated_client: FlaskClient,
) -> None:
    for number in range(27):
        create_organization(**organization_data(f"Organization {number:02d}"))

    first_page = authenticated_client.get("/organizations?page=1")
    second_page = authenticated_client.get("/organizations?page=2")

    assert first_page.data.count(b"<tr>") == 26
    assert b"Organization 00" in first_page.data
    assert b"Organization 25" not in first_page.data
    assert b"Organization 25" in second_page.data
