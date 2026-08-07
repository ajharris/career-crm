"""Task model, service, route, and workflow tests."""

from datetime import date, datetime, timedelta

import pytest

from app.extensions import db
from app.models.activity import Activity
from app.models.task import Task
from app.organizations.services import create_organization
from app.tasks.services import (
    complete_task,
    create_task,
    delete_task,
    list_tasks,
    reopen_task,
    update_task,
)
from app.utils.enums import OrganizationType, TaskPriority, TaskStatus, TaskType


def organization():
    return create_organization(
        name="UHN", organization_type=OrganizationType.HOSPITAL.value, priority=4
    )


def values(**extra):
    data = {
        "title": "Send follow-up",
        "task_type": TaskType.FOLLOW_UP.value,
        "priority": TaskPriority.MEDIUM.value,
        "status": TaskStatus.OPEN.value,
        "due_date": date.today() + timedelta(days=2),
    }
    data.update(extra)
    return data


def form_data(**extra):
    data = values()
    data["due_date"] = data["due_date"].isoformat()
    data.update(extra)
    return data


def test_model_defaults_and_overdue(app):
    task = create_task(**values(due_date=date.today() - timedelta(days=1)))
    assert task.priority is TaskPriority.MEDIUM
    assert task.status is TaskStatus.OPEN
    assert task.is_overdue
    assert task.created_at is not None


def test_validation_and_standalone_task(app):
    with pytest.raises(ValueError, match="title"):
        create_task(**values(title=" "))
    task = create_task(**values())
    assert task.organization is None


def test_relationship_and_set_null_history(app):
    org = organization()
    task = create_task(**values(organization_id=org.id))
    task_id = task.id
    db.session.delete(org)
    db.session.commit()
    assert db.session.get(Task, task_id).organization_id is None


def test_services_create_update_delete(app):
    task = create_task(**values())
    update_task(task, title="Updated", priority=TaskPriority.HIGH.value)
    assert task.title == "Updated" and task.priority is TaskPriority.HIGH
    task_id = task.id
    delete_task(task)
    assert db.session.get(Task, task_id) is None


def test_complete_reopen_and_activity(app):
    org = organization()
    task = create_task(**values(organization_id=org.id))
    complete_task(task)
    assert task.status is TaskStatus.COMPLETED and task.completed_at
    assert db.session.scalar(db.select(Activity).where(Activity.subject == task.title))
    reopen_task(task)
    assert task.status is TaskStatus.OPEN and task.completed_at is None


def test_list_search_filters_and_default_visibility(app):
    create_task(**values(title="Research UHN", priority=TaskPriority.HIGH.value))
    create_task(**values(title="Hidden", status=TaskStatus.COMPLETED.value))
    assert list_tasks(search="research", priority="high").total == 1
    assert list_tasks().total == 1
    assert list_tasks(completed_only=True).total == 1


def test_pagination(app):
    for index in range(26):
        create_task(**values(title=f"Task {index}"))
    page = list_tasks(page=2)
    assert page.total == 26 and len(page.items) == 1


def test_crud_routes(authenticated_client):
    response = authenticated_client.post(
        "/tasks/new", data=form_data(), follow_redirects=True
    )
    assert response.status_code == 200 and b"Task created successfully" in response.data
    task = db.session.scalar(db.select(Task))
    assert authenticated_client.get("/tasks").status_code == 200
    assert authenticated_client.get(f"/tasks/{task.id}").status_code == 200
    response = authenticated_client.post(
        f"/tasks/{task.id}/edit", data=form_data(title="Edited"), follow_redirects=True
    )
    assert b"Task updated successfully" in response.data
    response = authenticated_client.post(
        f"/tasks/{task.id}/complete", data={}, follow_redirects=True
    )
    assert b"Task completed successfully" in response.data
    response = authenticated_client.post(
        f"/tasks/{task.id}/delete", data={}, follow_redirects=True
    )
    assert b"Task deleted successfully" in response.data


def test_due_time_requires_date(authenticated_client):
    response = authenticated_client.post(
        "/tasks/new", data=form_data(due_date="", due_time="09:00")
    )
    assert b"due date is required" in response.data


def test_activity_followup_prefills_without_creating(authenticated_client, app):
    org = organization()
    activity = Activity(
        organization_id=org.id,
        activity_type="email",
        direction="outbound",
        occurred_at=datetime.now(),
        subject="Check in",
        follow_up_needed=True,
    )
    db.session.add(activity)
    db.session.commit()
    response = authenticated_client.get(f"/tasks/new?activity_id={activity.id}")
    assert b"Follow up: Check in" in response.data
    assert db.session.scalar(db.select(db.func.count(Task.id))) == 0
