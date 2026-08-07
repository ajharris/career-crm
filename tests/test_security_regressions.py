"""Security-focused regressions for ownership, CSRF, files, and API output."""

import io

from app import create_app
from app.extensions import db
from app.models import Application, Contact, Document, DocumentVersion, Task
from app.utils.enums import TaskType


def _api_token(client, email="test@example.com"):
    response = client.post(
        "/api/v1/token",
        json={"email": email, "password": "correct horse battery staple"},
    )
    return response.get_json()["access_token"]


def test_browser_mutations_require_csrf_outside_testing():
    app = create_app(
        {
            "TESTING": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "csrf-test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        response = app.test_client().post(
            "/auth/register",
            data={
                "first_name": "No",
                "last_name": "Token",
                "email": "csrf@example.com",
                "password": "long enough password",
                "confirm_password": "long enough password",
            },
        )
        assert response.status_code == 400


def test_private_records_are_absent_from_other_users_search_and_reports(
    authenticated_client, second_user, organization, job_posting
):
    private_contact = Contact(
        owner_id=second_user.id,
        organization_id=organization.id,
        first_name="Secret",
        last_name="Recruiter",
        email="private@example.com",
    )
    private_application = Application(
        owner_id=second_user.id, job_posting_id=job_posting.id
    )
    private_task = Task(
        owner_id=second_user.id,
        title="Secret follow-up",
        task_type=TaskType.FOLLOW_UP,
    )
    db.session.add_all([private_contact, private_application, private_task])
    db.session.commit()

    search = authenticated_client.get("/search?q=Secret")
    assert b"private@example.com" not in search.data
    assert b"Secret Recruiter" not in search.data
    report = authenticated_client.get("/reports/applications.csv")
    assert b"Fixture Engineer" not in report.data


def test_document_list_detail_and_download_resist_idor(
    app, authenticated_client, second_authenticated_client, tmp_path
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    response = second_authenticated_client.post(
        "/documents/new",
        data={
            "title": "Private Resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"private-data"), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    document = db.session.scalar(db.select(Document))
    version = document.versions[0]

    assert b"Private Resume" not in authenticated_client.get("/documents").data
    assert authenticated_client.get(f"/documents/{document.id}").status_code == 404
    assert (
        authenticated_client.get(
            f"/documents/versions/{version.id}/download"
        ).status_code
        == 404
    )


def test_document_download_blocks_storage_path_traversal(
    authenticated_client, user, tmp_path, app
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    secret = tmp_path / "secret.txt"
    secret.write_text("must-not-leak")
    document = Document(owner_id=user.id, title="Bad path", document_type="resume")
    version = DocumentVersion(
        document=document,
        version_number=1,
        original_filename="secret.txt",
        storage_name="../secret.txt",
        mime_type="text/plain",
        size_bytes=13,
    )
    db.session.add(version)
    db.session.commit()

    response = authenticated_client.get(f"/documents/versions/{version.id}/download")
    assert response.status_code == 404
    assert b"must-not-leak" not in response.data


def test_api_private_item_idor_and_sensitive_field_regression(
    client, user, second_user, job_posting
):
    private_application = Application(
        owner_id=second_user.id, job_posting_id=job_posting.id
    )
    db.session.add(private_application)
    db.session.commit()
    token = _api_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    assert (
        client.get(
            f"/api/v1/applications/{private_application.id}", headers=headers
        ).status_code
        == 404
    )
    response_text = client.get("/api/v1/applications", headers=headers).get_data(
        as_text=True
    )
    assert "password_hash" not in response_text
    assert "SECRET_KEY" not in response_text
    assert "access_token" not in response_text


def test_owner_id_payload_cannot_spoof_application_owner(
    authenticated_client, user, second_user, job_posting
):
    response = authenticated_client.post(
        "/applications/new",
        data={
            "job_posting_id": job_posting.id,
            "status": "planned",
            "owner_id": second_user.id,
        },
    )
    assert response.status_code == 302
    application = db.session.scalar(db.select(Application))
    assert application.owner_id == user.id


def test_shared_organization_delete_cannot_destroy_another_users_private_history(
    authenticated_client, second_user, organization, job_posting
):
    contact = Contact(
        owner_id=second_user.id,
        organization_id=organization.id,
        first_name="Second",
        last_name="Contact",
    )
    application = Application(owner_id=second_user.id, job_posting_id=job_posting.id)
    db.session.add_all([contact, application])
    db.session.commit()

    response = authenticated_client.post(f"/organizations/{organization.id}/delete")
    assert response.status_code == 409
    assert db.session.get(type(organization), organization.id) is not None
    assert db.session.get(Contact, contact.id) is not None
    assert db.session.get(Application, application.id) is not None


def test_shared_job_delete_cannot_destroy_another_users_application(
    authenticated_client, second_user, job_posting
):
    application = Application(owner_id=second_user.id, job_posting_id=job_posting.id)
    db.session.add(application)
    db.session.commit()
    response = authenticated_client.post(f"/jobs/{job_posting.id}/delete")
    assert response.status_code == 409
    assert db.session.get(type(job_posting), job_posting.id) is not None
    assert db.session.get(Application, application.id) is not None
