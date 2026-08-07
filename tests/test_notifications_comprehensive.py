"""Deterministic notification and reminder behavior."""

from datetime import UTC, date, datetime, time, timedelta

from flask_login import login_user

from app.extensions import db
from app.models import JobPosting, NotificationDismissal, Task
from app.notifications.services import notifications
from app.utils.enums import TaskStatus, TaskType


def test_notifications_classify_overdue_today_and_tomorrow(user, app):
    today = date.today()
    db.session.add_all(
        [
            Task(
                owner_id=user.id,
                title="Overdue",
                task_type=TaskType.FOLLOW_UP,
                due_date=today - timedelta(days=1),
            ),
            Task(
                owner_id=user.id,
                title="Today",
                task_type=TaskType.APPLICATION,
                due_date=today,
            ),
            Task(
                owner_id=user.id,
                title="Tomorrow",
                task_type=TaskType.INTERVIEW_PREPARATION,
                due_date=today + timedelta(days=1),
            ),
            Task(
                owner_id=user.id,
                title="Completed",
                task_type=TaskType.OTHER,
                status=TaskStatus.COMPLETED,
                due_date=today - timedelta(days=2),
            ),
        ]
    )
    db.session.commit()

    messages = {item["title"]: item["message"] for item in notifications()}
    assert messages == {
        "Overdue": "Task overdue.",
        "Today": "Task due today.",
        "Tomorrow": "Task due tomorrow.",
    }


def test_interview_and_shared_deadline_notifications(
    user, application, job_posting: JobPosting
):
    application.interview_date = datetime.combine(
        date.today(), time(hour=13), tzinfo=UTC
    )
    job_posting.closing_date = date.today() + timedelta(days=3)
    db.session.commit()

    items = notifications()
    assert any(item["message"] == "Interview today." for item in items)
    assert any("Application deadline" in item["message"] for item in items)


def test_notifications_do_not_include_another_users_private_tasks(
    user, second_user, app
):
    db.session.add(
        Task(
            owner_id=second_user.id,
            title="Other user's task",
            task_type=TaskType.FOLLOW_UP,
            due_date=date.today(),
        )
    )
    db.session.commit()
    with app.test_request_context():
        login_user(user)
        assert "Other user's task" not in {item["title"] for item in notifications()}


def test_dismissal_is_idempotent(authenticated_client, user):
    task = Task(
        owner_id=user.id,
        title="Dismiss once",
        task_type=TaskType.FOLLOW_UP,
        due_date=date.today(),
    )
    db.session.add(task)
    db.session.commit()
    key = f"task:{task.id}:{task.due_date}"

    first = authenticated_client.post("/notifications/dismiss", data={"key": key})
    second = authenticated_client.post("/notifications/dismiss", data={"key": key})
    assert first.status_code == second.status_code == 302
    count = db.session.scalar(
        db.select(db.func.count(NotificationDismissal.id)).where(
            NotificationDismissal.notification_key == key
        )
    )
    assert count == 1
