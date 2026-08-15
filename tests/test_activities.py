"""Activity model, service, route, and integration tests."""

from datetime import date, datetime

import pytest
from flask.testing import FlaskClient

from app.activities.services import (
    create_activity,
    delete_activity,
    list_activities,
    update_activity,
)
from app.applications.services import create_application
from app.contacts.services import create_contact
from app.extensions import db
from app.jobs.services import create_job_posting
from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.organizations.services import create_organization
from app.utils.enums import (
    ActivityDirection,
    ActivityType,
    ApplicationStatus,
    JobStatus,
    OrganizationType,
)


def make_organization(name: str = "UHN") -> Organization:
    """Create an organization used by activity tests."""
    return create_organization(
        name=name,
        organization_type=OrganizationType.HOSPITAL.value,
        priority=4,
    )


def make_contact(organization: Organization) -> Contact:
    """Create a contact used by activity tests."""
    return create_contact(
        organization_id=organization.id,
        first_name="Alex",
        last_name="Morgan",
        title="Hiring Manager",
    )


def make_job(
    organization: Organization, title: str = "Medical Physicist"
) -> JobPosting:
    """Create a job used by activity tests."""
    return create_job_posting(
        organization_id=organization.id,
        title=title,
        priority=4,
        status=JobStatus.DISCOVERED.value,
    )


def make_application(job: JobPosting) -> Application:
    """Create a planned application without automatic activity."""
    return create_application(
        job_posting_id=job.id,
        status=ApplicationStatus.PLANNED.value,
        accepted=False,
        withdrawn=False,
    )


def activity_data(organization_id: int) -> dict:
    """Return valid activity form data."""
    return {
        "organization_id": organization_id,
        "contact_id": "",
        "job_posting_id": "",
        "application_id": "",
        "activity_type": ActivityType.EMAIL.value,
        "occurred_at": "2026-08-05T14:30",
        "direction": ActivityDirection.OUTBOUND.value,
        "subject": "Hiring manager outreach",
        "summary": "Introduced myself and asked about the role.",
        "outcome": "Received a positive reply",
        "follow_up_needed": "y",
        "notes": "Follow up next week",
    }


def service_data(organization_id: int) -> dict:
    """Return activity data using native Python values."""
    values = activity_data(organization_id)
    values.update(
        contact_id=None,
        job_posting_id=None,
        application_id=None,
        occurred_at=datetime(2026, 8, 5, 14, 30),
        follow_up_needed=True,
    )
    return values


def test_activity_creation_enums_and_timestamps(app) -> None:
    organization = make_organization()

    activity = create_activity(**service_data(organization.id))

    assert activity.id is not None
    assert activity.activity_type is ActivityType.EMAIL
    assert activity.direction is ActivityDirection.OUTBOUND
    assert activity.created_at is not None
    assert activity.updated_at is not None


def test_activity_relationships_are_enriched(app) -> None:
    organization = make_organization()
    contact = make_contact(organization)
    job = make_job(organization)
    application = make_application(job)

    activity = create_activity(
        application_id=application.id,
        contact_id=contact.id,
        activity_type=ActivityType.INTERVIEW.value,
        occurred_at=datetime(2026, 8, 5, 14, 30),
        direction=ActivityDirection.INBOUND.value,
    )

    assert activity.organization is organization
    assert activity.contact is contact
    assert activity.job_posting is job
    assert activity.application is application


def test_activity_requires_related_entity(app) -> None:
    with pytest.raises(ValueError, match="At least one related entity"):
        create_activity(
            activity_type=ActivityType.RESEARCH.value,
            occurred_at=datetime(2026, 8, 5, 14, 30),
            direction=ActivityDirection.INTERNAL.value,
        )


def test_related_entity_delete_preserves_history(app) -> None:
    organization = make_organization()
    activity = create_activity(**service_data(organization.id))
    activity_id = activity.id

    db.session.delete(organization)
    db.session.commit()

    preserved = db.session.get(Activity, activity_id)
    assert preserved is not None
    assert preserved.organization_id is None


def test_create_update_delete_services(app) -> None:
    organization = make_organization()
    activity = create_activity(**service_data(organization.id))

    updated = update_activity(
        activity,
        subject="Updated outreach",
        outcome="Meeting booked",
    )
    assert updated.subject == "Updated outreach"
    assert updated.outcome == "Meeting booked"

    activity_id = activity.id
    delete_activity(activity)
    assert db.session.get(Activity, activity_id) is None


def test_list_and_detail_routes(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    activity = create_activity(**service_data(organization.id))

    listing = authenticated_client.get("/activities")
    detail = authenticated_client.get(f"/activities/{activity.id}")

    assert listing.status_code == 200
    assert b"Activity Timeline" in listing.data
    assert b"Hiring manager outreach" in listing.data
    assert detail.status_code == 200
    assert b"Received a positive reply" in detail.data


def test_create_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()

    response = authenticated_client.post(
        "/activities/new",
        data=activity_data(organization.id),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Activity created successfully." in response.data
    assert b"Hiring manager outreach" in response.data


def test_create_from_contact_uses_known_contact_context(
    authenticated_client: FlaskClient,
) -> None:
    organization = make_organization()
    contact = create_contact(
        organization_id=organization.id,
        first_name="Alex",
        last_name="Morgan",
        title="Hiring Manager",
        department="Medical Physics",
        email="alex@example.org",
        phone="416-555-0100",
    )

    form = authenticated_client.get(
        "/activities/new", query_string={"contact_id": contact.id}
    )

    assert form.status_code == 200
    assert b"Alex Morgan" in form.data
    assert b"Hiring Manager" in form.data
    assert b"Medical Physics" in form.data
    assert b"alex@example.org" in form.data
    assert b"416-555-0100" in form.data
    assert b"UHN" in form.data
    assert b'name="contact_id"' in form.data
    assert b'id="organization_id"' not in form.data
    assert b'id="contact_id"' not in form.data

    values = activity_data(organization.id)
    values.pop("organization_id")
    values["contact_id"] = contact.id
    response = authenticated_client.post(
        f"/activities/new?contact_id={contact.id}",
        data=values,
        follow_redirects=True,
    )

    assert response.status_code == 200
    activity = db.session.scalar(db.select(Activity))
    assert activity.contact_id == contact.id
    assert activity.organization_id == organization.id


def test_create_route_requires_relationship(authenticated_client: FlaskClient) -> None:
    values = activity_data(0)
    values["organization_id"] = ""

    response = authenticated_client.post("/activities/new", data=values)

    assert response.status_code == 200
    assert b"Select at least one related entity." in response.data


def test_edit_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    activity = create_activity(**service_data(organization.id))
    values = activity_data(organization.id)
    values["subject"] = "Edited subject"

    response = authenticated_client.post(
        f"/activities/{activity.id}/edit",
        data=values,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Activity updated successfully." in response.data
    assert activity.subject == "Edited subject"


def test_delete_requires_confirmation_and_deletes(
    authenticated_client: FlaskClient,
) -> None:
    organization = make_organization()
    activity = create_activity(**service_data(organization.id))
    activity_id = activity.id

    confirmation = authenticated_client.get(f"/activities/{activity_id}/delete")
    response = authenticated_client.post(
        f"/activities/{activity_id}/delete", follow_redirects=True
    )

    assert b"Are you sure" in confirmation.data
    assert b"Activity deleted successfully." in response.data
    assert db.session.get(Activity, activity_id) is None


@pytest.mark.parametrize(
    "query",
    ["hiring manager", "introduced", "positive reply", "follow up", "uhn", "alex"],
)
def test_search_is_case_insensitive(
    authenticated_client: FlaskClient, query: str
) -> None:
    organization = make_organization()
    contact = make_contact(organization)
    values = service_data(organization.id)
    values["contact_id"] = contact.id
    create_activity(**values)

    response = authenticated_client.get(
        "/activities", query_string={"q": query.upper()}
    )

    assert b"Hiring manager outreach" in response.data


def test_filters_combine_with_search(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    contact = make_contact(organization)
    job = make_job(organization)
    application = make_application(job)
    create_activity(
        organization_id=organization.id,
        contact_id=contact.id,
        job_posting_id=job.id,
        application_id=application.id,
        activity_type=ActivityType.INTERVIEW.value,
        occurred_at=datetime(2026, 8, 5, 14, 30),
        direction=ActivityDirection.INBOUND.value,
        subject="Technical discussion",
    )

    response = authenticated_client.get(
        "/activities",
        query_string={
            "q": "technical",
            "activity_type": ActivityType.INTERVIEW.value,
            "direction": ActivityDirection.INBOUND.value,
            "organization_id": organization.id,
            "contact_id": contact.id,
            "job_posting_id": job.id,
            "application_id": application.id,
            "date_from": "2026-08-01",
            "date_to": "2026-08-10",
        },
    )

    assert b"Technical discussion" in response.data


def test_default_timeline_order_and_sorting(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    older = service_data(organization.id)
    older.update(subject="Older", occurred_at=datetime(2026, 1, 1))
    newer = service_data(organization.id)
    newer.update(subject="Newer", occurred_at=datetime(2026, 2, 1))
    create_activity(**older)
    create_activity(**newer)

    default_response = authenticated_client.get("/activities")
    ascending = authenticated_client.get(
        "/activities?sort=occurred_at&sort_direction=asc"
    )

    assert default_response.data.index(b"Newer") < default_response.data.index(b"Older")
    assert ascending.data.index(b"Older") < ascending.data.index(b"Newer")


def test_pagination_displays_25_activities(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    for number in range(27):
        values = service_data(organization.id)
        values["subject"] = f"Activity {number:02d}"
        create_activity(**values)

    pagination = list_activities(page=1)
    second_pagination = list_activities(page=2, sort="created_at", sort_direction="asc")
    second_page = authenticated_client.get(
        "/activities?page=2&sort=created_at&sort_direction=asc"
    )

    assert len(pagination.items) == 25
    assert pagination.total == 27
    assert len(second_pagination.items) == 2
    assert b"Activity " in second_page.data


@pytest.mark.parametrize(
    ("query_name", "entity_factory"),
    [
        ("organization_id", lambda org: org),
        ("contact_id", lambda org: make_contact(org)),
        ("job_posting_id", lambda org: make_job(org)),
        ("application_id", lambda org: make_application(make_job(org))),
    ],
)
def test_context_aware_creation(
    authenticated_client: FlaskClient, query_name: str, entity_factory
) -> None:
    entity = entity_factory(make_organization())

    response = authenticated_client.get(
        "/activities/new", query_string={query_name: entity.id}
    )

    if query_name == "contact_id":
        assert f'name="contact_id" value="{entity.id}"'.encode() in response.data
    else:
        field_name = query_name
        assert f'name="{field_name}" value="{entity.id}"'.encode() in response.data


def test_contact_context_also_prefills_its_organization(
    authenticated_client: FlaskClient,
) -> None:
    organization = make_organization()
    contact = make_contact(organization)

    response = authenticated_client.get(
        "/activities/new", query_string={"contact_id": contact.id}
    )

    assert f'<option selected value="{contact.id}"'.encode() in response.data
    assert f'<option selected value="{organization.id}"'.encode() in response.data


def test_automatic_application_submitted_activity(app) -> None:
    job = make_job(make_organization())

    application = create_application(
        job_posting_id=job.id,
        application_date=date(2026, 8, 1),
        status=ApplicationStatus.APPLIED.value,
        accepted=False,
        withdrawn=False,
    )

    activity = db.session.scalar(
        db.select(Activity).where(Activity.application_id == application.id)
    )
    assert activity is not None
    assert activity.activity_type is ActivityType.APPLICATION_SUBMITTED
    assert activity.subject == "Applied for Medical Physicist"
    assert activity.organization_id == job.organization_id
    assert activity.job_posting_id == job.id


def test_planned_application_does_not_create_activity(app) -> None:
    application = make_application(make_job(make_organization()))

    assert (
        db.session.scalar(
            db.select(Activity).where(Activity.application_id == application.id)
        )
        is None
    )


def test_activity_integrations(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    contact = make_contact(organization)
    job = make_job(organization)
    application = make_application(job)
    create_activity(
        organization_id=organization.id,
        contact_id=contact.id,
        job_posting_id=job.id,
        application_id=application.id,
        activity_type=ActivityType.MEETING.value,
        occurred_at=datetime(2026, 8, 5, 14, 30),
        direction=ActivityDirection.INBOUND.value,
        subject="Integration activity",
    )

    responses = (
        authenticated_client.get(f"/organizations/{organization.id}"),
        authenticated_client.get(f"/contacts/{contact.id}"),
        authenticated_client.get(f"/jobs/{job.id}"),
        authenticated_client.get(f"/applications/{application.id}"),
        authenticated_client.get("/"),
    )

    assert all(b"Integration activity" in response.data for response in responses)
    assert all(b"Add Activity" in response.data for response in responses[:-1])
