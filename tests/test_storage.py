"""Instance Google Drive storage configuration and routing tests."""

import io
import json

from cryptography.fernet import Fernet

from app.ai.services import CredentialService
from app.extensions import db
from app.models import DocumentVersion, InstanceStorageConfiguration
from app.storage import services
from app.storage.services import StoredFile


def test_storage_settings_are_administrator_only(authenticated_client, admin_client):
    assert authenticated_client.get("/settings/storage").status_code == 403

    response = admin_client.get("/settings/storage")

    assert response.status_code == 200
    assert b"Instance Storage" in response.data
    assert b"Connect Google Drive" in response.data


def test_connect_starts_google_oauth_with_state(admin_client, app):
    app.config.update(
        GOOGLE_DRIVE_CLIENT_ID="client-id",
        GOOGLE_DRIVE_CLIENT_SECRET="client-secret",
    )

    response = admin_client.post("/settings/storage/connect/google-drive")

    assert response.status_code == 302
    assert response.location.startswith(services.AUTH_URL)
    assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file" in response.location
    with admin_client.session_transaction() as session:
        assert session["google_drive_oauth_state"]


def test_oauth_callback_rejects_invalid_state(admin_client):
    with admin_client.session_transaction() as session:
        session["google_drive_oauth_state"] = "expected"

    response = admin_client.get(
        "/settings/storage/callback/google-drive?state=wrong&code=code"
    )

    assert response.status_code == 400


def test_connect_encrypts_tokens_and_selects_drive(app, monkeypatch):
    app.config.update(
        GOOGLE_DRIVE_CLIENT_ID="client-id",
        GOOGLE_DRIVE_CLIENT_SECRET="client-secret",
        CREDENTIAL_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    )
    responses = iter(
        [
            {"access_token": "access", "refresh_token": "refresh"},
            {"user": {"emailAddress": "owner@example.com"}},
        ]
    )
    monkeypatch.setattr(services, "_json_request", lambda *args, **kwargs: next(responses))

    record = services.connect("code", "https://crm.example/callback")

    assert record.provider == "google_drive"
    assert record.account_email == "owner@example.com"
    assert "refresh" not in record.encrypted_credentials
    decrypted = CredentialService._cipher().decrypt(
        record.encrypted_credentials.encode()
    )
    assert json.loads(decrypted)["refresh_token"] == "refresh"


def test_document_upload_uses_configured_drive_and_download_redirects(
    authenticated_client, app, monkeypatch
):
    monkeypatch.setattr(
        services,
        "upload",
        lambda *args: StoredFile(
            "drive-file-id", "https://drive.google.com/file/d/drive-file-id/view"
        ),
    )

    response = authenticated_client.post(
        "/documents/new",
        data={
            "title": "Drive resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"resume"), "resume.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    version = db.session.scalar(db.select(DocumentVersion))
    assert version.storage_provider == "google_drive"
    assert version.storage_name == "drive-file-id"
    assert version.size_bytes == 6
    download = authenticated_client.get(f"/documents/versions/{version.id}/download")
    assert download.status_code == 302
    assert download.location == version.external_url


def test_disconnect_returns_instance_to_local_storage(app):
    record = InstanceStorageConfiguration(
        id=1,
        provider="google_drive",
        encrypted_credentials="encrypted",
        account_email="owner@example.com",
        folder_id="folder",
    )
    db.session.add(record)
    db.session.commit()

    services.disconnect()

    assert record.provider == "local"
    assert record.encrypted_credentials is None
    assert record.account_email is None
    assert record.folder_id is None
