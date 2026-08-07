"""Versioned JSON API and its OpenAPI contract."""

from datetime import date, datetime
from typing import Any

from flask import g, jsonify, request
from sqlalchemy import select

from app.api import bp
from app.api.auth import issue, verify
from app.auth.models import User
from app.extensions import db
from app.models import Activity, Application, JobPosting, Organization, Task


def serialize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return getattr(value, "value", value)


FIELDS: dict[str, tuple[Any, list[str]]] = {
    "organizations": (
        Organization,
        ["id", "name", "website", "location", "priority", "created_at"],
    ),
    "jobs": (
        JobPosting,
        [
            "id",
            "organization_id",
            "title",
            "location",
            "status",
            "priority",
            "closing_date",
        ],
    ),
    "applications": (
        Application,
        [
            "id",
            "job_posting_id",
            "application_date",
            "status",
            "interview_date",
            "notes",
        ],
    ),
    "activities": (
        Activity,
        [
            "id",
            "organization_id",
            "contact_id",
            "job_posting_id",
            "application_id",
            "activity_type",
            "occurred_at",
            "subject",
            "summary",
        ],
    ),
    "tasks": (
        Task,
        [
            "id",
            "organization_id",
            "contact_id",
            "job_posting_id",
            "application_id",
            "title",
            "status",
            "priority",
            "due_date",
        ],
    ),
}


@bp.before_request
def authenticate():
    if request.endpoint in ("api.token", "api.openapi"):
        return None
    auth = request.headers.get("Authorization", "")
    user_id = verify(auth[7:]) if auth.startswith("Bearer ") else None
    user = db.session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        return jsonify(error="invalid_token"), 401
    g.api_user = user


@bp.post("/token")
def token():
    data = request.get_json(silent=True) or {}
    user = db.session.scalar(
        select(User).where(User.email == str(data.get("email", "")).strip().lower())
    )
    if (
        user is None
        or not user.check_password(str(data.get("password", "")))
        or not user.is_active
    ):
        return jsonify(error="invalid_credentials"), 401
    return jsonify(access_token=issue(user.id), token_type="Bearer", expires_in=3600)


@bp.get("/<resource>")
def collection(resource):
    if resource not in FIELDS:
        return jsonify(error="not_found"), 404
    model, fields = FIELDS[resource]
    query = select(model)
    if hasattr(model, "owner_id"):
        query = query.where(model.owner_id == g.api_user.id)
    page = max(request.args.get("page", 1, type=int), 1)
    per = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    records = list(
        db.session.scalars(
            query.order_by(model.id.desc()).offset((page - 1) * per).limit(per)
        )
    )
    return jsonify(
        data=[{f: serialize(getattr(row, f)) for f in fields} for row in records],
        page=page,
        per_page=per,
    )


@bp.get("/<resource>/<int:record_id>")
def item(resource, record_id):
    if resource not in FIELDS:
        return jsonify(error="not_found"), 404
    model, fields = FIELDS[resource]
    row = db.session.get(model, record_id)
    if row is None or (hasattr(row, "owner_id") and row.owner_id != g.api_user.id):
        return jsonify(error="not_found"), 404
    return jsonify({f: serialize(getattr(row, f)) for f in fields})


@bp.get("/openapi.json")
def openapi():
    paths = {
        f"/api/v1/{name}": {
            "get": {
                "summary": f"List {name}",
                "security": [{"bearerAuth": []}],
                "responses": {"200": {"description": "Paginated records"}},
            }
        }
        for name in FIELDS
    }
    paths["/api/v1/token"] = {
        "post": {
            "summary": "Issue an access token",
            "responses": {"200": {"description": "JWT"}},
        }
    }
    return jsonify(
        openapi="3.1.0",
        info={"title": "Career CRM API", "version": "1.0.0"},
        paths=paths,
        components={
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    )
