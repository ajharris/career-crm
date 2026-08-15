"""Per-user Google Drive and Gmail connection tests."""

import base64
import io
import json
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet

from app.ai.services import CredentialService
from app.extensions import db
from app.integrations import services
from app.models import DocumentVersion, GoogleAccountConnection
from app.storage import services as storage_services


def configure_google(app):
    app.config.update(
        GOOGLE_CLIENT_ID="google-client",
        GOOGLE_CLIENT_SECRET="google-secret",
        CREDENTIAL_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    )


def test_existing_user_can_open_connected_accounts(authenticated_client):
    response = authenticated_client.get("/settings/integrations")

    assert response.status_code == 200
    assert b"Connected Accounts" in response.data
    assert b"Connect Google Drive" in response.data
    assert b"Connect Gmail" in response.data


def test_connect_requests_drive_only(authenticated_client, app):
    configure_google(app)

    response = authenticated_client.post(
        "/settings/integrations/google/drive/connect",
        data={"google_email": "personal@gmail.com"},
    )

    assert response.status_code == 302
    query = parse_qs(urlparse(response.location).query)
    assert query["scope"] == [services.DRIVE_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["include_granted_scopes"] == ["false"]
    assert query["login_hint"] == ["personal@gmail.com"]
    with authenticated_client.session_transaction() as session:
        assert session["google_drive_oauth_state"]


def test_gmail_authorization_is_separate_from_drive(authenticated_client, app):
    configure_google(app)

    response = authenticated_client.post("/settings/integrations/google/gmail/connect")

    query = parse_qs(urlparse(response.location).query)
    assert query["scope"] == [services.GMAIL_SEND_SCOPE]
    assert services.DRIVE_SCOPE not in query["scope"][0]


def test_callback_rejects_wrong_state(authenticated_client):
    with authenticated_client.session_transaction() as session:
        session["google_drive_oauth_state"] = "expected"

    response = authenticated_client.get(
        "/settings/integrations/google/drive/callback?state=wrong&code=code"
    )

    assert response.status_code == 400


def test_connection_is_encrypted_and_owned_by_existing_user(app, user, monkeypatch):
    configure_google(app)
    replies = iter(
        [
            {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "scope": services.DRIVE_SCOPE,
            },
            {"user": {"emailAddress": "career@example.com"}},
        ]
    )
    monkeypatch.setattr(services, "_json_request", lambda *args, **kwargs: next(replies))

    record = services.connect(
        user.id,
        "drive",
        "code",
        "https://crm.example/callback",
        "career@example.com",
    )

    assert record.user_id == user.id
    assert record.service == "drive"
    assert record.account_email == "career@example.com"
    assert "refresh-secret" not in record.encrypted_credentials
    decrypted = CredentialService._cipher().decrypt(record.encrypted_credentials.encode())
    assert json.loads(decrypted)["refresh_token"] == "refresh-secret"


def test_connection_refuses_a_different_google_account(app, user, monkeypatch):
    configure_google(app)
    replies = iter(
        [
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "scope": services.DRIVE_SCOPE,
            },
            {"user": {"emailAddress": "university@example.edu"}},
        ]
    )
    monkeypatch.setattr(services, "_json_request", lambda *args, **kwargs: next(replies))

    import pytest

    with pytest.raises(RuntimeError, match="No connection was saved"):
        services.connect(
            user.id,
            "drive",
            "code",
            "https://crm.example/callback",
            "personal@gmail.com",
        )

    assert services.connection_for(user.id, "drive") is None


def test_connections_are_isolated_per_crm_user(app, user, second_user):
    first = GoogleAccountConnection(
        user_id=user.id,
        service="drive",
        account_email="first@example.com",
        encrypted_credentials="first-secret",
        granted_scopes=services.DRIVE_SCOPE,
    )
    second = GoogleAccountConnection(
        user_id=second_user.id,
        service="gmail",
        account_email="second@example.com",
        encrypted_credentials="second-secret",
        granted_scopes=services.GMAIL_SEND_SCOPE,
    )
    db.session.add_all([first, second])
    db.session.commit()

    assert services.connection_for(user.id, "drive") is first
    assert services.connection_for(second_user.id, "gmail") is second


def test_gmail_send_uses_connected_account_without_read_scope(app, user, monkeypatch):
    configure_google(app)
    token = {
        "access_token": "old",
        "refresh_token": "refresh",
        "scope": services.GMAIL_SEND_SCOPE,
    }
    record = GoogleAccountConnection(
        user_id=user.id,
        service="gmail",
        account_email="sender@example.com",
        encrypted_credentials=CredentialService._cipher().encrypt(
            json.dumps(token).encode()
        ).decode(),
        granted_scopes=services.GMAIL_SEND_SCOPE,
    )
    db.session.add(record)
    db.session.commit()
    requests = []

    def fake_request(url, **kwargs):
        requests.append((url, kwargs))
        return {"access_token": "fresh"} if url == services.TOKEN_URL else {"id": "msg-1"}

    monkeypatch.setattr(services, "_json_request", fake_request)

    message_id = services.send_email(
        user.id, "contact@example.com", "Hello", "Following up."
    )

    assert message_id == "msg-1"
    assert requests[-1][0] == services.GMAIL_SEND_URL
    encoded = json.loads(requests[-1][1]["data"])["raw"]
    decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    assert b"To: contact@example.com" in decoded
    assert b"Subject: Hello" in decoded


def test_users_drive_is_used_for_their_document_upload(
    authenticated_client, app, user, monkeypatch
):
    record = GoogleAccountConnection(
        user_id=user.id,
        service="drive",
        account_email="owner@example.com",
        encrypted_credentials="encrypted",
        granted_scopes=services.DRIVE_SCOPE,
        drive_folder_id="career-crm-folder",
    )
    db.session.add(record)
    db.session.commit()
    requests = []
    monkeypatch.setattr(services, "access_token", lambda connection: "access")

    def fake_request(url, **kwargs):
        requests.append((url, kwargs))
        return {
            "id": "personal-drive-file",
            "webViewLink": "https://drive.google.com/file/d/personal-drive-file/view",
        }

    monkeypatch.setattr(storage_services, "_json_request", fake_request)

    response = authenticated_client.post(
        "/documents/new",
        data={
            "title": "Personal resume",
            "document_type": "resume",
            "file": (io.BytesIO(b"resume"), "resume.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    version = db.session.scalar(db.select(DocumentVersion))
    assert version.storage_provider == "google_drive"
    assert version.storage_name == "personal-drive-file"
    assert b"career-crm-folder" in requests[0][1]["data"]


def test_disconnect_removes_only_current_users_connection(app, user, second_user):
    records = [
        GoogleAccountConnection(
            user_id=account.id,
            service="drive",
            account_email=f"{account.id}@example.com",
            encrypted_credentials="secret",
            granted_scopes=services.DRIVE_SCOPE,
        )
        for account in (user, second_user)
    ]
    db.session.add_all(records)
    db.session.commit()

    services.disconnect(user.id, "drive")

    assert services.connection_for(user.id, "drive") is None
    assert services.connection_for(second_user.id, "drive") is not None
