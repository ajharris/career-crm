"""Tests for dashboard analytics and saved widgets."""

from datetime import date, timedelta

from app.applications.services import create_application
from app.dashboard.services import dashboard_data, get_widget_preferences
from app.extensions import db
from app.integrations.services import DRIVE_SCOPE, GMAIL_SEND_SCOPE
from app.jobs.services import create_job_posting
from app.models import GoogleAccountConnection
from app.organizations.services import create_organization
from app.tasks.services import create_task
from app.utils.enums import (
    ApplicationStatus,
    JobStatus,
    OrganizationType,
    TaskPriority,
    TaskStatus,
    TaskType,
)


def organization():
    return create_organization(
        name="Analytics Co",
        organization_type=OrganizationType.HEALTH_TECH.value,
        priority=4,
    )


def job(org, **extra):
    values = {
        "organization_id": org.id,
        "title": "Data Scientist",
        "priority": 4,
        "status": JobStatus.APPLIED.value,
    }
    values.update(extra)
    return create_job_posting(**values)


def test_dashboard_returns_structured_charts_and_rates(app):
    org = organization()
    role = job(org)
    create_application(
        job_posting_id=role.id,
        status=ApplicationStatus.PHONE_INTERVIEW.value,
        application_date=date.today(),
    )

    data = dashboard_data()

    assert data["insights"] == {
        "applications_this_month": 1,
        "interview_rate": 100.0,
        "response_rate": 100.0,
    }
    assert isinstance(data["chart_data"]["pipeline"]["labels"], list)
    assert sum(data["chart_data"]["pipeline"]["values"]) == 1


def test_upcoming_deadlines_merge_tasks_and_closing_dates(app):
    org = organization()
    due = date.today() + timedelta(days=3)
    job(org, closing_date=due)
    create_task(
        organization_id=org.id,
        title="Prepare documents",
        task_type=TaskType.DOCUMENT_PREPARATION.value,
        priority=TaskPriority.HIGH.value,
        status=TaskStatus.OPEN.value,
        due_date=due - timedelta(days=1),
    )

    deadlines = dashboard_data()["upcoming_deadlines"]

    assert [item["kind"] for item in deadlines] == ["Task", "Posting closes"]
    assert all(isinstance(item["parameters"], dict) for item in deadlines)


def test_saved_widget_visibility(authenticated_client, app):
    response = authenticated_client.post(
        "/dashboard/settings",
        data={"tasks": "y", "deadlines": "y", "submit": "Save dashboard"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Dashboard widgets saved." in response.data
    assert b"Hiring Pipeline" not in response.data
    preferences = {item["key"]: item["enabled"] for item in get_widget_preferences()}
    assert preferences["tasks"] and preferences["deadlines"]
    assert not preferences["pipeline"] and not preferences["organizations"]


def test_dashboard_shows_google_connect_action(authenticated_client):
    response = authenticated_client.get("/")

    assert response.status_code == 200
    assert b"Google integrations" in response.data
    assert b"Connect Google Drive" in response.data


def test_dashboard_shows_connected_google_account(authenticated_client, user):
    db.session.add(
        GoogleAccountConnection(
            user_id=user.id,
            service="drive",
            account_email="career@example.com",
            encrypted_credentials="encrypted",
            granted_scopes=f"{DRIVE_SCOPE} {GMAIL_SEND_SCOPE}",
        )
    )
    db.session.commit()

    response = authenticated_client.get("/")

    assert response.status_code == 200
    assert b"career@example.com" in response.data
    assert b"Manage Google integrations" in response.data
