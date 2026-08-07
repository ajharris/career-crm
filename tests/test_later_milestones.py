"""Integration coverage for milestones 12 through 24."""

import io
from datetime import date, timedelta

from app.extensions import db
from app.models import Application, JobPosting, Organization, Skill, Task
from app.utils.enums import TaskType


def _records(user):
    organization = Organization(
        name="Future Labs", created_by_id=user.id, updated_by_id=user.id
    )
    job = JobPosting(
        title="Platform Engineer",
        organization=organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    application = Application(owner_id=user.id, job_posting=job)
    task = Task(
        owner_id=user.id,
        title="Follow up",
        task_type=TaskType.FOLLOW_UP,
        due_date=date.today() - timedelta(days=1),
    )
    db.session.add_all([application, task])
    db.session.commit()
    return organization, job, application


def test_document_upload_version_and_download(
    authenticated_client, user, app, tmp_path
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    response = authenticated_client.post(
        "/documents/new",
        data={
            "title": "Resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"resume"), "resume.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200 and b"v1" in response.data
    from app.models import Document

    document = db.session.scalar(db.select(Document))
    version = document.versions[0]
    download = authenticated_client.get(f"/documents/versions/{version.id}/download")
    assert download.data == b"resume"


def test_search_reports_and_notifications(authenticated_client, user):
    _records(user)
    assert b"Platform Engineer" in authenticated_client.get("/search?q=Platform").data
    assert authenticated_client.get("/reports/applications.csv").status_code == 200
    assert authenticated_client.get("/reports/applications.xlsx").data.startswith(b"PK")
    assert authenticated_client.get("/reports/applications.pdf").data.startswith(
        b"%PDF"
    )
    assert b"overdue" in authenticated_client.get("/notifications").data


def test_api_token_collections_and_openapi(client, user):
    token = client.post(
        "/api/v1/token",
        json={"email": user.email, "password": "correct horse battery staple"},
    ).get_json()["access_token"]
    response = client.get(
        "/api/v1/applications", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200 and "data" in response.get_json()
    assert client.get("/api/v1/openapi.json").get_json()["openapi"] == "3.1.0"


def test_importer_contract(tmp_path):
    path = tmp_path / "jobs.csv"
    path.write_text("title,organization\nEngineer,Acme\n")
    from app.commands.import_jobs import CSVJobImporter

    assert list(CSVJobImporter(path).load())[0].organization == "Acme"


def test_saved_search_create_and_delete(authenticated_client):
    response = authenticated_client.post(
        "/search?q=python&type=jobs", data={"name": "Python roles"}
    )
    assert response.status_code == 302
    from app.models import SavedSearch

    saved = db.session.scalar(db.select(SavedSearch))
    assert saved.query == "python"
    assert (
        authenticated_client.post(f"/search/saved/{saved.id}/delete").status_code == 302
    )
    assert db.session.get(SavedSearch, saved.id) is None


def test_job_skill_management(authenticated_client, user):
    _, job, _ = _records(user)
    skill = Skill(
        name="Kubernetes",
        category="cloud",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.session.add(skill)
    db.session.commit()
    response = authenticated_client.post(
        f"/skills/jobs/{job.id}",
        data={"skill_id": skill.id, "importance": 4, "required": "y"},
    )
    assert response.status_code == 302 and job.skill_requirements[0].importance == 4
    record = job.skill_requirements[0]
    assert (
        authenticated_client.post(
            f"/skills/jobs/{job.id}/{record.id}/delete"
        ).status_code
        == 302
    )


def test_document_new_version_and_application_attachment(
    authenticated_client, user, app, tmp_path
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    _, _, application = _records(user)
    authenticated_client.post(
        "/documents/new",
        data={
            "title": "Letter",
            "document_type": "cover_letter",
            "file": (io.BytesIO(b"v1"), "letter.txt"),
        },
        content_type="multipart/form-data",
    )
    from app.models import Document

    document = db.session.scalar(db.select(Document))
    authenticated_client.post(
        f"/documents/{document.id}",
        data={"file": (io.BytesIO(b"v2"), "letter.txt"), "submit": "Add version"},
        content_type="multipart/form-data",
    )
    assert len(document.versions) == 2
    authenticated_client.post(
        f"/documents/{document.id}/attach",
        data={"application_id": application.id, "purpose": "submission"},
    )
    db.session.refresh(application)
    assert application.document_links[0].version.version_number == 2


def test_collaboration_notes_review_and_moderation(authenticated_client, user):
    organization, _, _ = _records(user)
    authenticated_client.post(
        f"/community/organizations/{organization.id}",
        data={"kind": "note", "body": "Helpful recruiter"},
    )
    authenticated_client.post(
        f"/community/organizations/{organization.id}",
        data={"kind": "review", "body": "Good process", "rating": 4},
    )
    from app.models import CompanyReview, OrganizationNote

    assert db.session.scalar(db.select(OrganizationNote)).body == "Helpful recruiter"
    review = db.session.scalar(db.select(CompanyReview))
    user.is_admin = True
    db.session.commit()
    assert (
        authenticated_client.post(
            f"/community/reviews/{review.id}/moderate", data={"status": "approved"}
        ).status_code
        == 302
    )
    assert review.moderation_status == "approved"


def test_ai_prompt_and_disabled_provider(app):
    from app.ai.services import build_prompt, generate

    assert build_prompt("match", {"skills": ["Python"]})["context"]["skills"] == [
        "Python"
    ]
    with app.test_request_context():
        try:
            generate("match", {})
        except RuntimeError as exc:
            assert "not configured" in str(exc)
        else:
            raise AssertionError("disabled provider should fail")


def test_ai_assistant_page_and_generation(authenticated_client, user, monkeypatch):
    _records(user)
    assert authenticated_client.get("/assistant").status_code == 200
    monkeypatch.setattr(
        "app.ai.routes.generate", lambda task, context: "Reviewable draft"
    )
    application = db.session.scalar(db.select(Application))
    response = authenticated_client.post(
        "/assistant",
        data={
            "application_id": application.id,
            "task": "job_summary",
            "notes": "Focus on platform work",
        },
    )
    assert b"Reviewable draft" in response.data


def test_health_and_security_headers(client):
    response = client.get("/health")
    assert response.get_json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_api_items_and_invalid_tokens(client, user):
    _, job, _ = _records(user)
    token = client.post(
        "/api/v1/token",
        json={"email": user.email, "password": "correct horse battery staple"},
    ).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.get(f"/api/v1/jobs/{job.id}", headers=headers).get_json()["title"]
        == "Platform Engineer"
    )
    assert client.get("/api/v1/nope", headers=headers).status_code == 404
    assert (
        client.get(
            "/api/v1/tasks", headers={"Authorization": "Bearer broken"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/token", json={"email": user.email, "password": "bad"}
        ).status_code
        == 401
    )


def test_notification_dismissal(authenticated_client, user):
    _records(user)
    authenticated_client.get("/notifications")
    from app.notifications.services import notifications

    key = notifications()[0]["key"]
    assert (
        authenticated_client.post(
            "/notifications/dismiss", data={"key": key}
        ).status_code
        == 302
    )
    assert key not in {item["key"] for item in notifications()}


def test_importer_persists_and_deduplicates(app, user, tmp_path):
    path = tmp_path / "jobs.csv"
    path.write_text("title,organization,location\nEngineer,Acme,Remote\n")
    from app.commands.import_jobs import CSVJobImporter, persist

    assert persist(CSVJobImporter(path), user.id) == 1
    assert persist(CSVJobImporter(path), user.id) == 0


def test_job_registry():
    from app.performance import JobRegistry

    registry = JobRegistry()
    registry.register("answer", lambda: 42)
    assert registry.names == ("answer",) and registry.run("answer") == 42
