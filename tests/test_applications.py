"""Application model, service, and route tests."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from flask.testing import FlaskClient
from sqlalchemy.exc import IntegrityError

from app.applications.services import (
    DuplicateApplicationError,
    create_application,
    delete_application,
    list_applications,
    update_application,
)
from app.extensions import db
from app.jobs.services import create_job_posting
from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.organizations.services import create_organization
from app.utils.enums import ApplicationStatus, JobStatus, OrganizationType


def make_organization(name: str = "UHN") -> Organization:
    """Create an organization used by application tests."""
    return create_organization(
        name=name,
        organization_type=OrganizationType.HOSPITAL.value,
        priority=4,
    )


def make_job(
    organization: Organization, title: str = "Medical Physicist"
) -> JobPosting:
    """Create a job posting used by application tests."""
    return create_job_posting(
        organization_id=organization.id,
        title=title,
        priority=4,
        status=JobStatus.DISCOVERED.value,
    )


def application_data(job_id: int) -> dict:
    """Return valid form data."""
    return {
        "job_posting_id": job_id,
        "application_date": "2026-08-10",
        "status": ApplicationStatus.APPLIED.value,
        "source": "Company website",
        "resume_version": "https://docs.google.com/document/d/resume-uhn",
        "cover_letter_version": "https://docs.google.com/document/d/cl-uhn",
        "recruiter_name": "Jordan Recruiter",
        "recruiter_email": "jordan@example.org",
        "salary_requested": "120000.00",
        "interview_date": "2026-08-15T10:00",
        "interview_location": "Video call",
        "rejection_reason": "",
        "offer_salary": "125000.00",
        "accepted": "y",
        "withdrawn": "",
        "notes": "Strong application",
    }


def service_data(job_id: int) -> dict:
    """Return application data using native Python values."""
    values = application_data(job_id)
    values.update(
        application_date=date(2026, 8, 10),
        salary_requested=Decimal("120000.00"),
        interview_date=datetime(2026, 8, 15, 10, 0),
        offer_salary=Decimal("125000.00"),
        accepted=True,
        withdrawn=False,
    )
    return values


def test_application_creation_and_relationship(app) -> None:
    organization = make_organization()
    job = make_job(organization)

    application = create_application(**service_data(job.id))

    assert application.id is not None
    assert application.job_posting is job
    assert job.applications == [application]
    assert application.job_posting.organization is organization


def test_application_status_is_constrained(app) -> None:
    application = Application(job_posting_id=1, status=ApplicationStatus.PLANNED)

    assert application.status is ApplicationStatus.PLANNED
    with pytest.raises(ValueError, match="Invalid application status"):
        cast(Any, application).status = "unknown"


def test_one_application_per_job_database_constraint(app) -> None:
    organization = make_organization()
    job = make_job(organization)
    db.session.add(Application(job_posting_id=job.id, status=ApplicationStatus.PLANNED))
    db.session.commit()
    db.session.add(Application(job_posting_id=job.id, status=ApplicationStatus.APPLIED))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_duplicate_application_service_error(app) -> None:
    organization = make_organization()
    job = make_job(organization)
    create_application(**service_data(job.id))

    with pytest.raises(DuplicateApplicationError, match="already has"):
        create_application(**service_data(job.id))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"salary_requested": Decimal("0")}, "Salary requested"),
        ({"offer_salary": Decimal("-1")}, "Offer salary"),
        (
            {
                "application_date": date(2026, 8, 10),
                "interview_date": datetime(2026, 8, 9, 10, 0),
            },
            "Interview date",
        ),
    ],
)
def test_application_service_validation(app, changes: dict, message: str) -> None:
    organization = make_organization()
    job = make_job(organization)
    values = service_data(job.id)
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        create_application(**values)


def test_deleting_job_cascades_to_application(app) -> None:
    organization = make_organization()
    job = make_job(organization)
    application = create_application(**service_data(job.id))
    application_id = application.id

    db.session.delete(job)
    db.session.commit()

    assert db.session.get(Application, application_id) is None


def test_create_application_service(app) -> None:
    job = make_job(make_organization())

    application = create_application(**service_data(job.id))

    assert db.session.get(Application, application.id) is application
    assert application.status is ApplicationStatus.APPLIED


def test_update_application_service(app) -> None:
    job = make_job(make_organization())
    application = create_application(**service_data(job.id))

    updated = update_application(
        application,
        status=ApplicationStatus.SCREENING.value,
        recruiter_name="New Recruiter",
    )

    assert updated.status is ApplicationStatus.SCREENING
    assert updated.recruiter_name == "New Recruiter"


def test_delete_application_service(app) -> None:
    job = make_job(make_organization())
    application = create_application(**service_data(job.id))
    application_id = application.id

    delete_application(application)

    assert db.session.get(Application, application_id) is None


def test_list_route(authenticated_client: FlaskClient) -> None:
    response = authenticated_client.get("/applications")

    assert response.status_code == 200
    assert b"New Application" in response.data


def test_create_and_detail_routes(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())

    response = authenticated_client.post(
        "/applications/new",
        data=application_data(job.id),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Application created successfully." in response.data
    assert b"Medical Physicist" in response.data
    assert b"Open r\xc3\xa9sum\xc3\xa9" in response.data


def test_create_route_validates_fields(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    values = application_data(job.id)
    values.update(
        resume_version="invalid",
        recruiter_email="invalid",
        salary_requested="0",
        offer_salary="-1",
        application_date="2026-08-10",
        interview_date="2026-08-09T10:00",
    )

    response = authenticated_client.post("/applications/new", data=values)

    assert response.status_code == 200
    assert b"Invalid URL." in response.data
    assert b"Invalid email address." in response.data
    assert b"Number must be at least 0.01." in response.data
    assert b"Interview date cannot precede" in response.data


def test_new_application_preselects_job(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())

    response = authenticated_client.get(f"/applications/new?job_posting_id={job.id}")

    assert f'<option selected value="{job.id}"'.encode() in response.data


def test_edit_route(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    application = create_application(**service_data(job.id))
    values = application_data(job.id)
    values["status"] = ApplicationStatus.OFFER.value

    response = authenticated_client.post(
        f"/applications/{application.id}/edit",
        data=values,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Application updated successfully." in response.data
    assert application.status is ApplicationStatus.OFFER


def test_delete_requires_confirmation(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    application = create_application(**service_data(job.id))

    response = authenticated_client.get(f"/applications/{application.id}/delete")

    assert response.status_code == 200
    assert b"Are you sure" in response.data


def test_delete_route(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    application = create_application(**service_data(job.id))
    application_id = application.id

    response = authenticated_client.post(
        f"/applications/{application_id}/delete", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Application deleted successfully." in response.data
    assert db.session.get(Application, application_id) is None


@pytest.mark.parametrize(
    "query", ["uhn", "physicist", "jordan", "resume-uhn", "strong application"]
)
def test_search_is_case_insensitive(
    authenticated_client: FlaskClient, query: str
) -> None:
    job = make_job(make_organization())
    create_application(**service_data(job.id))

    response = authenticated_client.get(
        "/applications", query_string={"q": query.upper()}
    )

    assert b"Medical Physicist" in response.data


def test_filters_combine_with_search(authenticated_client: FlaskClient) -> None:
    first_org = make_organization("UHN")
    second_org = make_organization("PocketHealth")
    first_job = make_job(first_org, "Medical Physicist")
    second_job = make_job(second_org, "Software Engineer")
    create_application(**service_data(first_job.id))
    second_values = service_data(second_job.id)
    second_values.update(
        status=ApplicationStatus.ACCEPTED.value,
        application_date=date(2025, 5, 1),
        accepted=True,
        withdrawn=False,
    )
    create_application(**second_values)

    response = authenticated_client.get(
        "/applications",
        query_string={
            "q": "software",
            "status": ApplicationStatus.ACCEPTED.value,
            "organization_id": second_org.id,
            "applied_year": 2025,
            "accepted": "true",
            "withdrawn": "false",
        },
    )

    assert b"Software Engineer" in response.data
    assert b"Medical Physicist" not in response.data


def test_sorting(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    alpha = make_job(organization, "Alpha Role")
    zulu = make_job(organization, "Zulu Role")
    create_application(**service_data(alpha.id))
    create_application(**service_data(zulu.id))

    response = authenticated_client.get("/applications?sort=job_title&direction=desc")

    assert response.data.index(b"Zulu Role") < response.data.index(b"Alpha Role")


def test_pagination_displays_25_applications(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    for number in range(27):
        job = make_job(organization, f"Role {number:02d}")
        create_application(**service_data(job.id))

    pagination = list_applications(page=1)
    second_page = authenticated_client.get(
        "/applications?page=2&sort=job_title&direction=asc"
    )

    assert len(pagination.items) == 25
    assert pagination.total == 27
    assert b"Role 25" in second_page.data


def test_job_detail_application_integration(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    without_application = authenticated_client.get(f"/jobs/{job.id}")
    application = create_application(**service_data(job.id))

    with_application = authenticated_client.get(f"/jobs/{job.id}")

    assert b"Create Application" in without_application.data
    assert b"View Application" in with_application.data
    assert b"Create Application" not in with_application.data
    assert str(application.id).encode() in with_application.data


def test_dashboard_application_count(authenticated_client: FlaskClient) -> None:
    job = make_job(make_organization())
    create_application(**service_data(job.id))

    response = authenticated_client.get("/")

    assert b"Applications" in response.data
    assert b'<p class="display-6 mb-0">1</p>' in response.data
