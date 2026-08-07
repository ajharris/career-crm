"""Document validation, versioning, association, and missing-file behavior."""

import io

from app.extensions import db
from app.models import ApplicationDocument, Document


def test_upload_rejects_missing_and_unsupported_files(authenticated_client):
    missing = authenticated_client.post(
        "/documents/new", data={"title": "Missing", "document_type": "resume"}
    )
    unsupported = authenticated_client.post(
        "/documents/new",
        data={
            "title": "Executable",
            "document_type": "resume",
            "file": (io.BytesIO(b"binary"), "resume.exe"),
        },
        content_type="multipart/form-data",
    )
    assert missing.status_code == unsupported.status_code == 200
    assert b"This field is required" in missing.data
    assert b"Unsupported file type" in unsupported.data
    assert db.session.scalar(db.select(db.func.count(Document.id))) == 0


def test_missing_backing_file_returns_404(authenticated_client, app, tmp_path, user):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    authenticated_client.post(
        "/documents/new",
        data={
            "title": "Soon Missing",
            "document_type": "resume",
            "file": (io.BytesIO(b"contents"), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    document = db.session.scalar(db.select(Document))
    version = document.versions[0]
    (tmp_path / version.storage_name).unlink()
    assert (
        authenticated_client.get(
            f"/documents/versions/{version.id}/download"
        ).status_code
        == 404
    )


def test_attaching_latest_version_is_idempotent(
    authenticated_client, application, app, tmp_path
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    authenticated_client.post(
        "/documents/new",
        data={
            "title": "Resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"v1"), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    document = db.session.scalar(db.select(Document))
    for _ in range(2):
        response = authenticated_client.post(
            f"/documents/{document.id}/attach",
            data={"application_id": application.id, "purpose": "submitted"},
        )
        assert response.status_code == 302
    assert db.session.scalar(db.select(db.func.count(ApplicationDocument.id))) == 1


def test_document_cannot_attach_to_another_users_application(
    authenticated_client, second_user, job_posting, app, tmp_path
):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    other_application = __import__("app.models", fromlist=["Application"]).Application(
        owner_id=second_user.id, job_posting_id=job_posting.id
    )
    db.session.add(other_application)
    db.session.commit()
    authenticated_client.post(
        "/documents/new",
        data={
            "title": "Resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"v1"), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    document = db.session.scalar(db.select(Document))
    response = authenticated_client.post(
        f"/documents/{document.id}/attach",
        data={"application_id": other_application.id},
    )
    assert response.status_code == 302
    assert db.session.scalar(db.select(db.func.count(ApplicationDocument.id))) == 0
