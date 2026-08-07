"""Global search and structured/exported report behavior."""

import csv
import io
from datetime import UTC, date, datetime
from zipfile import ZipFile

from app.extensions import db
from app.models import Activity, Application, Contact, JobPosting
from app.utils.enums import ActivityDirection, ActivityType, ApplicationStatus


def test_global_search_is_case_insensitive_and_type_filtered(
    authenticated_client, user, organization, job_posting
):
    contact = Contact(
        owner_id=user.id,
        organization_id=organization.id,
        first_name="Ada",
        last_name="Lovelace",
    )
    job_posting.title = "PYTHON Engineer"
    db.session.add(contact)
    db.session.commit()
    all_results = authenticated_client.get("/search?q=python")
    contacts_only = authenticated_client.get("/search?q=python&type=contacts")
    assert b"PYTHON Engineer" in all_results.data
    assert b"PYTHON Engineer" not in contacts_only.data
    assert b"Ada Lovelace" in authenticated_client.get("/search?q=ada").data


def test_search_treats_sql_wildcards_as_literal_characters(
    authenticated_client, organization
):
    organization.name = "Ordinary Employer"
    db.session.commit()
    response = authenticated_client.get("/search?q=%25&type=organizations")
    assert b"Ordinary Employer" not in response.data


def test_empty_and_invalid_search_filters_are_safe(authenticated_client):
    assert authenticated_client.get("/search").status_code == 200
    response = authenticated_client.get("/search?q=test&type=not-a-real-type")
    assert response.status_code == 200
    assert b"Global search" in response.data


def test_duplicate_saved_search_name_is_handled_without_server_error(
    authenticated_client,
):
    first = authenticated_client.post(
        "/search?q=python&type=jobs", data={"name": "Engineering"}
    )
    second = authenticated_client.post(
        "/search?q=sql&type=jobs", data={"name": "Engineering"}
    )
    assert first.status_code == second.status_code == 302
    from app.models import SavedSearch

    searches = list(db.session.scalars(db.select(SavedSearch)))
    assert len(searches) == 1
    assert searches[0].query == "sql"


def test_report_data_contains_month_recruiter_and_organization_history(
    authenticated_client, user, application, organization
):
    application.application_date = date(2026, 8, 1)
    application.status = ApplicationStatus.PHONE_INTERVIEW
    application.recruiter_name = "Casey Recruiter"
    activity = Activity(
        owner_id=user.id,
        organization_id=organization.id,
        activity_type=ActivityType.EMAIL,
        direction=ActivityDirection.OUTBOUND,
        occurred_at=datetime.now(UTC),
        subject="Follow-up",
    )
    db.session.add(activity)
    db.session.commit()
    response = authenticated_client.get("/reports")
    assert b"2026-08" in response.data
    assert b"Casey Recruiter" in response.data
    assert b"Fixture Organization" in response.data


def test_csv_xlsx_and_pdf_exports_are_structurally_valid_and_scoped(
    authenticated_client, user, second_user, application, job_posting
):
    application.application_date = date(2026, 8, 2)
    application.recruiter_name = "Renée, Recruiter"
    private_job = JobPosting(
        title="Other User Secret",
        organization=job_posting.organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.session.add(private_job)
    db.session.flush()
    db.session.add(Application(owner_id=second_user.id, job_posting=private_job))
    db.session.commit()

    csv_response = authenticated_client.get("/reports/applications.csv")
    decoded = csv_response.data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(decoded)))
    assert rows[0] == [
        "Application date",
        "Organization",
        "Job",
        "Status",
        "Recruiter",
        "Interview date",
    ]
    assert len(rows) == 2
    assert rows[1][4] == "Renée, Recruiter"
    assert "Other User Secret" not in decoded

    xlsx_response = authenticated_client.get("/reports/applications.xlsx")
    with ZipFile(io.BytesIO(xlsx_response.data)) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
    pdf_response = authenticated_client.get("/reports/applications.pdf")
    assert pdf_response.data.startswith(b"%PDF-1.4")
    assert pdf_response.data.rstrip().endswith(b"%%EOF")


def test_empty_report_exports_have_headers_and_no_data_rows(authenticated_client):
    csv_response = authenticated_client.get("/reports/applications.csv")
    rows = list(csv.reader(io.StringIO(csv_response.data.decode("utf-8-sig"))))
    assert len(rows) == 1
    assert authenticated_client.get("/reports/applications.xlsx").status_code == 200
    assert authenticated_client.get("/reports/applications.pdf").status_code == 200
