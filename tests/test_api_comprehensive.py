"""REST API authentication, pagination, serialization, and failure behavior."""

import base64
import json

from app.api.auth import issue, verify
from app.extensions import db
from app.models import Application, Task
from app.utils.enums import TaskType

PASSWORD = "correct horse battery staple"


def _token(client, email="test@example.com", password=PASSWORD):
    return client.post("/api/v1/token", json={"email": email, "password": password})


def test_token_rejects_missing_malformed_and_unknown_credentials(client):
    assert client.post("/api/v1/token").status_code == 401
    assert (
        client.post(
            "/api/v1/token", data="{bad", content_type="application/json"
        ).status_code
        == 401
    )
    assert _token(client, "missing@example.com").status_code == 401
    assert _token(client, password="wrong password").status_code == 401
    assert _token(client, password="wrong password").get_json() == {
        "error": "invalid_credentials"
    }


def test_bearer_auth_rejects_missing_corrupt_and_expired_tokens(client, user, app):
    assert client.get("/api/v1/tasks").status_code == 401
    assert (
        client.get(
            "/api/v1/tasks", headers={"Authorization": "Bearer corrupt"}
        ).status_code
        == 401
    )
    with app.test_request_context():
        expired = issue(user.id, ttl=-1)
        assert verify(expired) is None
    assert (
        client.get(
            "/api/v1/tasks", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )


def test_jwt_header_and_payload_are_standard_and_non_sensitive(client):
    token = _token(client).get_json()["access_token"]
    header_part, payload_part, _ = token.split(".")
    header = json.loads(base64.urlsafe_b64decode(header_part + "=="))
    payload = json.loads(base64.urlsafe_b64decode(payload_part + "=="))
    assert header == {"alg": "HS256", "typ": "JWT"}
    assert payload["sub"].isdigit()
    assert set(payload) == {"sub", "iat", "exp"}


def test_collection_pagination_and_maximum_page_size(client, user):
    db.session.add_all(
        [
            Task(owner_id=user.id, title=f"Task {index}", task_type=TaskType.OTHER)
            for index in range(105)
        ]
    )
    db.session.commit()
    token = _token(client).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = client.get("/api/v1/tasks?per_page=10&page=1", headers=headers).get_json()
    second = client.get("/api/v1/tasks?per_page=10&page=2", headers=headers).get_json()
    capped = client.get("/api/v1/tasks?per_page=1000", headers=headers).get_json()
    assert len(first["data"]) == len(second["data"]) == 10
    assert {row["id"] for row in first["data"]}.isdisjoint(
        {row["id"] for row in second["data"]}
    )
    assert len(capped["data"]) == capped["per_page"] == 100


def test_api_serializes_dates_and_enums(client, application: Application):
    application.application_date = __import__("datetime").date.today()
    db.session.commit()
    token = _token(client).get_json()["access_token"]
    response = client.get(
        f"/api/v1/applications/{application.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    payload = response.get_json()
    assert payload["application_date"] == application.application_date.isoformat()
    assert payload["status"] == application.status.value


def test_openapi_declares_every_implemented_collection(client):
    document = client.get("/api/v1/openapi.json").get_json()
    assert document["openapi"] == "3.1.0"
    assert set(document["paths"]) == {
        "/api/v1/token",
        "/api/v1/organizations",
        "/api/v1/jobs",
        "/api/v1/applications",
        "/api/v1/activities",
        "/api/v1/tasks",
    }
    assert document["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
