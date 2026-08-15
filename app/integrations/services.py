"""Secure per-user Google Drive and Gmail OAuth integration."""

import base64
import json
import secrets
from email.message import EmailMessage
from urllib.parse import urlencode

from cryptography.fernet import InvalidToken
from flask import current_app
from sqlalchemy import select

from app.ai.services import CredentialService
from app.extensions import db
from app.models.integration import GoogleAccountConnection
from app.storage.services import ABOUT_URL, AUTH_URL, TOKEN_URL, _json_request

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SERVICE_SCOPES = {"drive": DRIVE_SCOPE, "gmail": GMAIL_SEND_SCOPE}
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def connection_for(user_id: int, service: str) -> GoogleAccountConnection | None:
    _scope_for(service)
    return db.session.scalar(
        select(GoogleAccountConnection).where(
            GoogleAccountConnection.user_id == user_id,
            GoogleAccountConnection.service == service,
        )
    )


def authorization_url(
    service: str, redirect_uri: str, login_hint: str | None = None
) -> tuple[str, str]:
    client_id, _ = _client_credentials()
    scope = _scope_for(service)
    state = secrets.token_urlsafe(32)
    parameters = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "include_granted_scopes": "false",
        "prompt": "consent select_account",
        "state": state,
    }
    if login_hint:
        parameters["login_hint"] = login_hint
    return f"{AUTH_URL}?{urlencode(parameters)}", state


def connect(
    user_id: int,
    service: str,
    code: str,
    redirect_uri: str,
    expected_email: str | None = None,
) -> GoogleAccountConnection:
    if not code:
        raise ValueError("Google did not return an authorization code.")
    client_id, client_secret = _client_credentials()
    token_payload = _json_request(
        TOKEN_URL,
        data=urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if not token_payload.get("access_token"):
        raise RuntimeError("Google did not return usable account credentials.")
    scope = _scope_for(service)
    existing = connection_for(user_id, service)
    if "refresh_token" not in token_payload and existing is not None:
        previous = _decrypt(existing)
        token_payload["refresh_token"] = previous.get("refresh_token")
    if not token_payload.get("refresh_token"):
        raise RuntimeError("Google did not return reusable account credentials.")
    account = _json_request(ABOUT_URL, token=token_payload["access_token"])
    email = account.get("user", {}).get("emailAddress")
    if not email:
        raise RuntimeError("Google did not return the connected account identity.")
    if expected_email and email.casefold() != expected_email.casefold():
        raise RuntimeError(
            f"Google authorized {email}, not the requested account {expected_email}. "
            "No connection was saved. Try again in a private browser window."
        )
    granted = set(token_payload.get("scope", "").split())
    if not granted:
        granted = {scope}
    if scope not in granted:
        raise RuntimeError(f"Google did not grant the requested {service.title()} access.")
    record = existing or GoogleAccountConnection(user_id=user_id, service=service)
    record.account_email = email
    record.granted_scopes = " ".join(sorted(granted))
    record.encrypted_credentials = _encrypt(token_payload)
    db.session.add(record)
    db.session.commit()
    return record


def disconnect(user_id: int, service: str) -> None:
    if record := connection_for(user_id, service):
        db.session.delete(record)
        db.session.commit()


def save_drive_folder(user_id: int, folder_id: str | None) -> None:
    record = connection_for(user_id, "drive")
    if record is None or not record.has_scope(DRIVE_SCOPE):
        raise RuntimeError("Connect Google Drive before selecting a folder.")
    record.drive_folder_id = folder_id.strip() if folder_id and folder_id.strip() else None
    db.session.commit()


def access_token(record: GoogleAccountConnection) -> str:
    payload = _decrypt(record)
    client_id, client_secret = _client_credentials()
    refreshed = _json_request(
        TOKEN_URL,
        data=urlencode(
            {
                "refresh_token": payload["refresh_token"],
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload.update(refreshed)
    record.encrypted_credentials = _encrypt(payload)
    db.session.commit()
    return payload["access_token"]


def send_email(user_id: int, recipient: str, subject: str, body: str) -> str:
    """Send one plain-text message without granting mailbox read access."""
    record = connection_for(user_id, "gmail")
    if record is None or not record.has_scope(GMAIL_SEND_SCOPE):
        raise RuntimeError("Connect Gmail before sending email.")
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = record.account_email
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
    result = _json_request(
        GMAIL_SEND_URL,
        data=json.dumps({"raw": raw}).encode(),
        token=access_token(record),
        headers={"Content-Type": "application/json"},
    )
    return result["id"]


def _client_credentials() -> tuple[str, str]:
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = current_app.config.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Google OAuth client credentials are not configured.")
    return client_id, client_secret


def _scope_for(service: str) -> str:
    try:
        return SERVICE_SCOPES[service]
    except KeyError as exc:
        raise ValueError("Unsupported Google service.") from exc


def _encrypt(payload: dict) -> str:
    return CredentialService._cipher().encrypt(json.dumps(payload).encode()).decode()


def _decrypt(record: GoogleAccountConnection) -> dict:
    try:
        return json.loads(
            CredentialService._cipher()
            .decrypt(record.encrypted_credentials.encode())
            .decode()
        )
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Stored Google credentials cannot be decrypted.") from exc
