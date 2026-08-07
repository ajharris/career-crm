"""Cross-user ownership, authorization, and query-isolation tests."""

from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from flask import g
from flask_login import login_user

from app.activities.services import create_activity, list_activities
from app.applications.services import create_application, list_applications
from app.auth.models import User
from app.auth.services import create_user
from app.contacts.services import create_contact, list_contacts
from app.dashboard.services import dashboard_data
from app.extensions import db
from app.jobs.services import create_job_posting
from app.models.contact import Contact
from app.organizations.services import create_organization
from app.tasks.services import create_task, list_tasks
from app.utils.enums import (
    ActivityDirection,
    ActivityType,
    ApplicationStatus,
    JobStatus,
    OrganizationType,
    TaskPriority,
    TaskStatus,
    TaskType,
)

PASSWORD = "correct horse battery staple"


@pytest.fixture
def second_user(app) -> User:
    user = create_user(
        first_name="Second",
        last_name="User",
        email="second@example.com",
        password=PASSWORD,
    )
    assert user.career_profile is not None
    user.career_profile.onboarding_completed = True
    db.session.commit()
    return user


@contextmanager
def acting_as(app, user):
    """Run service-layer operations as a specific authenticated account."""
    with app.test_request_context():
        g.pop("_login_user", None)
        login_user(user)
        try:
            yield
        finally:
            g.pop("_login_user", None)


def logged_in_client(app, user):
    client = app.test_client()
    response = client.post(
        "/auth/login", data={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 302
    return client


def shared_records(app, creator):
    with acting_as(app, creator):
        organization = create_organization(
            name="Shared Health",
            organization_type=OrganizationType.HEALTH_TECH.value,
            priority=4,
        )
        job = create_job_posting(
            organization_id=organization.id,
            title="Shared Role",
            priority=4,
            status=JobStatus.APPLIED.value,
        )
    return organization, job


def private_records(app, owner, organization, job, suffix):
    with acting_as(app, owner):
        contact = create_contact(
            organization_id=organization.id,
            first_name=suffix,
            last_name="Private Contact",
        )
        application = create_application(
            job_posting_id=job.id,
            status=ApplicationStatus.PLANNED.value,
            application_date=date.today(),
        )
        activity = create_activity(
            organization_id=organization.id,
            contact_id=contact.id,
            activity_type=ActivityType.EMAIL.value,
            occurred_at=datetime.now(UTC),
            direction=ActivityDirection.OUTBOUND.value,
            subject=f"{suffix} private activity",
        )
        task = create_task(
            organization_id=organization.id,
            contact_id=contact.id,
            title=f"{suffix} private task",
            task_type=TaskType.FOLLOW_UP.value,
            priority=TaskPriority.MEDIUM.value,
            status=TaskStatus.OPEN.value,
        )
    return contact, application, activity, task


def test_private_lists_search_and_detail_routes_are_isolated(
    app, authenticated_client, user, second_user
):
    organization, job = shared_records(app, user)
    own = private_records(app, user, organization, job, "Owner")
    other = private_records(app, second_user, organization, job, "Hidden")

    paths = ("contacts", "applications", "activities", "tasks")
    for path, own_record, other_record in zip(paths, own, other, strict=True):
        listing = authenticated_client.get(f"/{path}")
        assert listing.status_code == 200
        assert b"Hidden private" not in listing.data
        assert authenticated_client.get(f"/{path}/{own_record.id}").status_code == 200
        assert authenticated_client.get(f"/{path}/{other_record.id}").status_code == 404
        assert (
            authenticated_client.get(f"/{path}/{other_record.id}/edit").status_code
            == 404
        )
        assert (
            authenticated_client.get(f"/{path}/{other_record.id}/delete").status_code
            == 404
        )

    with acting_as(app, user):
        assert list_contacts(search="Hidden").total == 0
        assert list_applications().total == 1
        assert list_activities(search="Hidden").total == 0
        assert list_tasks(search="Hidden").total == 0


def test_private_creation_sets_owner_and_ignores_spoofed_id(
    app, authenticated_client, user, second_user
):
    organization, _ = shared_records(app, user)
    response = authenticated_client.post(
        "/contacts/new",
        data={
            "organization_id": organization.id,
            "first_name": "Form",
            "last_name": "Owner",
            "priority": 3,
            "owner_id": second_user.id,
        },
    )
    assert response.status_code == 302
    contact = db.session.scalar(db.select(Contact).where(Contact.first_name == "Form"))
    assert contact.owner_id == user.id


def test_shared_visibility_creator_permissions_and_admin_override(
    app, authenticated_client, user, second_user
):
    organization, job = shared_records(app, user)
    assert organization.created_by_id == organization.updated_by_id == user.id
    assert job.created_by_id == job.updated_by_id == user.id

    other_client = logged_in_client(app, second_user)
    assert other_client.get(f"/organizations/{organization.id}").status_code == 200
    assert other_client.get(f"/jobs/{job.id}").status_code == 200
    assert other_client.get(f"/organizations/{organization.id}/edit").status_code == 403
    assert (
        other_client.get(f"/organizations/{organization.id}/delete").status_code == 403
    )
    assert other_client.get(f"/jobs/{job.id}/edit").status_code == 403
    assert other_client.get(f"/jobs/{job.id}/delete").status_code == 403

    second_user.is_admin = True
    db.session.commit()
    assert other_client.get(f"/organizations/{organization.id}/edit").status_code == 200
    assert other_client.get(f"/jobs/{job.id}/edit").status_code == 200


def test_shared_detail_integrations_and_dashboard_do_not_leak(
    app, authenticated_client, user, second_user
):
    organization, job = shared_records(app, user)
    private_records(app, second_user, organization, job, "Hidden")

    organization_page = authenticated_client.get(
        f"/organizations/{organization.id}"
    ).data
    job_page = authenticated_client.get(f"/jobs/{job.id}").data
    assert b"Hidden" not in organization_page
    assert b"Hidden" not in job_page

    with acting_as(app, user):
        data = dashboard_data()
    cards = {label: count for label, count, _, _ in data["summary_cards"]}
    assert cards["Organizations"] == 1
    assert cards["Job Postings"] == 1
    assert cards["Contacts"] == 0
    assert cards["Applications"] == 0
    assert cards["Open Tasks"] == 0
    assert data["recent_activities"] == []


def test_each_user_may_apply_to_the_same_shared_job(app, user, second_user):
    _, job = shared_records(app, user)
    with acting_as(app, user):
        first = create_application(
            job_posting_id=job.id, status=ApplicationStatus.PLANNED.value
        )
    with acting_as(app, second_user):
        second = create_application(
            job_posting_id=job.id, status=ApplicationStatus.PLANNED.value
        )
    assert first.owner_id == user.id
    assert second.owner_id == second_user.id
    assert len(job.applications) == 2
