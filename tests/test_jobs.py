"""Job posting model, service, and route tests."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.jobs.services import (
    create_job_posting,
    delete_job_posting,
    list_job_postings,
    update_job_posting,
)
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.organizations.services import create_organization
from app.utils.enums import (
    EmploymentType,
    JobSource,
    JobStatus,
    OrganizationType,
    WorkMode,
)


def make_organization(name: str = "UHN") -> Organization:
    """Create an organization used by job tests."""
    return create_organization(
        name=name,
        organization_type=OrganizationType.HOSPITAL.value,
        location="Toronto",
        priority=4,
    )


def job_data(organization_id: int, title: str = "Medical Physicist") -> dict:
    """Return valid form data."""
    return {
        "organization_id": organization_id,
        "title": title,
        "department": "Radiation Medicine",
        "location": "Toronto",
        "employment_type": EmploymentType.FULL_TIME.value,
        "work_mode": WorkMode.HYBRID.value,
        "salary_min": "90000.00",
        "salary_max": "120000.00",
        "salary_currency": "CAD",
        "posting_url": "https://example.org/jobs/1",
        "source": JobSource.COMPANY_WEBSITE.value,
        "date_posted": "2026-08-01",
        "closing_date": "2026-08-31",
        "discovered_at": "2026-08-02T09:30",
        "priority": 5,
        "status": JobStatus.DISCOVERED.value,
        "description": "Clinical physics opportunity",
        "notes": "Strong fit",
    }


def service_data(organization_id: int, title: str = "Medical Physicist") -> dict:
    """Return job data using native Python field values."""
    values = job_data(organization_id, title)
    values.update(
        salary_min=Decimal("90000.00"),
        salary_max=Decimal("120000.00"),
        date_posted=date(2026, 8, 1),
        closing_date=date(2026, 8, 31),
        discovered_at=datetime(2026, 8, 2, 9, 30),
    )
    return values


def test_job_model_creation_and_relationship(app) -> None:
    organization = make_organization()

    job = create_job_posting(**service_data(organization.id))

    assert job.id is not None
    assert job.organization is organization
    assert job in organization.job_postings
    assert job.created_at is not None
    assert job.updated_at is not None


def test_job_enumerated_fields(app) -> None:
    organization = make_organization()

    job = create_job_posting(**service_data(organization.id))

    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.work_mode is WorkMode.HYBRID
    assert job.status is JobStatus.DISCOVERED
    assert job.source is JobSource.COMPANY_WEBSITE


def test_job_requires_title(app) -> None:
    with pytest.raises(ValueError, match="title is required"):
        JobPosting(organization_id=1, title=" ", priority=3)


def test_job_rejects_invalid_priority(app) -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        JobPosting(organization_id=1, title="Role", priority=6)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"salary_min": Decimal("10"), "salary_max": Decimal("5")}, "salary"),
        (
            {"date_posted": date(2026, 8, 10), "closing_date": date(2026, 8, 1)},
            "Closing date",
        ),
    ],
)
def test_job_service_validates_ranges(app, changes: dict, message: str) -> None:
    organization = make_organization()
    values = service_data(organization.id)
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        create_job_posting(**values)


def test_deleting_organization_cascades_to_jobs(app) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))
    job_id = job.id

    db.session.delete(organization)
    db.session.commit()

    assert db.session.get(JobPosting, job_id) is None


def test_create_job_service(app) -> None:
    organization = make_organization()

    job = create_job_posting(**service_data(organization.id))

    assert db.session.get(JobPosting, job.id) is job
    assert job.title == "Medical Physicist"


def test_update_job_service(app) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))

    updated = update_job_posting(
        job, title="Senior Medical Physicist", status=JobStatus.RESEARCHING.value
    )

    assert updated.title == "Senior Medical Physicist"
    assert updated.status is JobStatus.RESEARCHING


def test_delete_job_service(app) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))
    job_id = job.id

    delete_job_posting(job)

    assert db.session.get(JobPosting, job_id) is None


def test_list_route(authenticated_client: FlaskClient) -> None:
    response = authenticated_client.get("/jobs")

    assert response.status_code == 200
    assert b"New Job Posting" in response.data


def test_create_and_detail_routes(authenticated_client: FlaskClient) -> None:
    organization = make_organization()

    response = authenticated_client.post(
        "/jobs/new", data=job_data(organization.id), follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Job posting created successfully." in response.data
    assert b"Medical Physicist" in response.data
    assert b"Company Website" in response.data


def test_create_route_validates_url_and_ranges(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    values = job_data(organization.id)
    values.update(
        title="",
        posting_url="invalid",
        salary_min="120000",
        salary_max="90000",
        date_posted="2026-08-20",
        closing_date="2026-08-10",
    )

    response = authenticated_client.post("/jobs/new", data=values)

    assert response.status_code == 200
    assert b"This field is required." in response.data
    assert b"Invalid URL." in response.data
    assert b"Maximum salary must be at least" in response.data
    assert b"Closing date cannot precede" in response.data


def test_new_job_preselects_organization(authenticated_client: FlaskClient) -> None:
    organization = make_organization()

    response = authenticated_client.get(f"/jobs/new?organization_id={organization.id}")

    assert f'<option selected value="{organization.id}"'.encode() in response.data


def test_edit_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))
    values = job_data(organization.id, "Senior Physicist")
    values["status"] = JobStatus.READY_TO_APPLY.value

    response = authenticated_client.post(f"/jobs/{job.id}/edit", data=values, follow_redirects=True)

    assert response.status_code == 200
    assert b"Job posting updated successfully." in response.data
    assert job.title == "Senior Physicist"


def test_delete_requires_confirmation(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))

    response = authenticated_client.get(f"/jobs/{job.id}/delete")

    assert response.status_code == 200
    assert b"Are you sure" in response.data
    assert db.session.get(JobPosting, job.id) is job


def test_delete_route(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    job = create_job_posting(**service_data(organization.id))
    job_id = job.id

    response = authenticated_client.post(f"/jobs/{job_id}/delete", follow_redirects=True)

    assert response.status_code == 200
    assert b"Job posting deleted successfully." in response.data
    assert db.session.get(JobPosting, job_id) is None


@pytest.mark.parametrize(
    "query", ["physicist", "UHN", "radiation", "clinical", "strong fit"]
)
def test_search_is_case_insensitive(authenticated_client: FlaskClient, query: str) -> None:
    organization = make_organization()
    create_job_posting(**service_data(organization.id))

    response = authenticated_client.get("/jobs", query_string={"q": query.upper()})

    assert b"Medical Physicist" in response.data


def test_filters_combine_with_search(authenticated_client: FlaskClient) -> None:
    first = make_organization("UHN")
    second = make_organization("PocketHealth")
    create_job_posting(**service_data(first.id, "Clinical Physicist"))
    other = service_data(second.id, "Software Engineer")
    other.update(
        status=JobStatus.RESEARCHING.value,
        employment_type=EmploymentType.CONTRACT.value,
        work_mode=WorkMode.REMOTE.value,
        priority=2,
    )
    create_job_posting(**other)

    response = authenticated_client.get(
        "/jobs",
        query_string={
            "q": "software",
            "organization_id": second.id,
            "status": JobStatus.RESEARCHING.value,
            "employment_type": EmploymentType.CONTRACT.value,
            "work_mode": WorkMode.REMOTE.value,
            "priority": 2,
        },
    )

    assert b"Software Engineer" in response.data
    assert b"Clinical Physicist" not in response.data


def test_sorting(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    create_job_posting(**service_data(organization.id, "Alpha Role"))
    create_job_posting(**service_data(organization.id, "Zulu Role"))

    response = authenticated_client.get("/jobs?sort=title&direction=desc")

    assert response.data.index(b"Zulu Role") < response.data.index(b"Alpha Role")


def test_pagination_displays_25_jobs(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    for number in range(27):
        create_job_posting(**service_data(organization.id, f"Role {number:02d}"))

    pagination = list_job_postings(page=1)
    second_page = authenticated_client.get("/jobs?page=2&sort=title&direction=asc")

    assert len(pagination.items) == 25
    assert pagination.total == 27
    assert b"Role 25" in second_page.data


def test_organization_detail_lists_only_active_jobs(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    create_job_posting(**service_data(organization.id, "Active Role"))
    closed = service_data(organization.id, "Closed Role")
    closed["status"] = JobStatus.CLOSED.value
    create_job_posting(**closed)

    response = authenticated_client.get(f"/organizations/{organization.id}")

    assert b"Add Job Posting" in response.data
    assert b"Active Role" in response.data
    assert b"Closed Role" not in response.data


def test_dashboard_job_count(authenticated_client: FlaskClient) -> None:
    organization = make_organization()
    create_job_posting(**service_data(organization.id))

    response = authenticated_client.get("/")

    marker = b'<h2 class="h6 text-body-secondary">Job Postings</h2>'
    assert marker in response.data
    assert b'<p class="display-6 mb-0">1</p>' in response.data
