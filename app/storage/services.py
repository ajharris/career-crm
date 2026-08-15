"""Google Drive OAuth and instance document-storage services."""

import json
import secrets
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import InvalidToken
from flask import current_app

from app.ai.services import CredentialService
from app.extensions import db
from app.models.storage import InstanceStorageConfiguration

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
ABOUT_URL = "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)"
SCOPE = "https://www.googleapis.com/auth/drive.file"


@dataclass(frozen=True)
class StoredFile:
    identifier: str
    web_url: str | None


def configuration() -> InstanceStorageConfiguration:
    record = db.session.get(InstanceStorageConfiguration, 1)
    if record is None:
        record = InstanceStorageConfiguration(id=1)
        db.session.add(record)
        db.session.commit()
    return record


def oauth_authorization_url(redirect_uri: str) -> tuple[str, str]:
    client_id = current_app.config.get("GOOGLE_DRIVE_CLIENT_ID")
    if not client_id or not current_app.config.get("GOOGLE_DRIVE_CLIENT_SECRET"):
        raise RuntimeError("Google Drive OAuth client credentials are not configured.")
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}", state


def connect(code: str, redirect_uri: str) -> InstanceStorageConfiguration:
    payload = _json_request(
        TOKEN_URL,
        data=urlencode(
            {
                "code": code,
                "client_id": current_app.config["GOOGLE_DRIVE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_DRIVE_CLIENT_SECRET"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise RuntimeError("Google did not return reusable Drive credentials.")
    account = _json_request(ABOUT_URL, token=payload["access_token"])
    record = configuration()
    record.provider = "google_drive"
    record.encrypted_credentials = CredentialService._cipher().encrypt(
        json.dumps(payload).encode()
    ).decode()
    record.account_email = account.get("user", {}).get("emailAddress")
    db.session.commit()
    return record


def disconnect() -> None:
    record = configuration()
    record.provider = "local"
    record.encrypted_credentials = None
    record.account_email = None
    record.folder_id = None
    db.session.commit()


def set_folder(folder_id: str | None) -> None:
    record = configuration()
    record.folder_id = folder_id.strip() if folder_id and folder_id.strip() else None
    db.session.commit()


def upload(filename: str, mime_type: str, content: bytes) -> StoredFile | None:
    record = configuration()
    if record.provider != "google_drive":
        return None
    token = _access_token(record)
    metadata: dict[str, object] = {"name": filename}
    if record.folder_id:
        metadata["parents"] = [record.folder_id]
    boundary = f"career-crm-{secrets.token_hex(12)}"
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    result = _json_request(
        f"{UPLOAD_URL}?uploadType=multipart&fields=id,webViewLink",
        data=body,
        token=token,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
    )
    return StoredFile(result["id"], result.get("webViewLink"))


def _access_token(record: InstanceStorageConfiguration) -> str:
    if not record.encrypted_credentials:
        raise RuntimeError("Google Drive is not connected.")
    try:
        payload = json.loads(
            CredentialService._cipher()
            .decrypt(record.encrypted_credentials.encode())
            .decode()
        )
    except (InvalidToken, json.JSONDecodeError) as exc:
        raise RuntimeError("Stored Google Drive credentials cannot be decrypted.") from exc
    # Refresh on each upload. This avoids depending on provider-specific expiry clocks.
    refreshed = _json_request(
        TOKEN_URL,
        data=urlencode(
            {
                "refresh_token": payload["refresh_token"],
                "client_id": current_app.config["GOOGLE_DRIVE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_DRIVE_CLIENT_SECRET"],
                "grant_type": "refresh_token",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload.update(refreshed)
    record.encrypted_credentials = CredentialService._cipher().encrypt(
        json.dumps(payload).encode()
    ).decode()
    db.session.commit()
    return payload["access_token"]


def _json_request(
    url: str,
    *,
    data: bytes | None = None,
    token: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, data=data, headers=request_headers), timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Google Drive is temporarily unavailable.") from exc
