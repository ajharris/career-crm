"""Secure document persistence."""

from pathlib import Path
from uuid import uuid4

from flask import current_app
from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.auth.permissions import actor_id
from app.extensions import db
from app.models.application import Application
from app.models.document import ApplicationDocument, Document, DocumentVersion


def list_documents():
    return list(
        db.session.scalars(
            select(Document)
            .where(Document.owner_id == actor_id())
            .order_by(Document.created_at.desc())
        )
    )


def get_document(document_id: int) -> Document:
    return (
        db.get_or_404(Document, document_id)
        if db.session.scalar(
            select(Document.id).where(
                Document.id == document_id, Document.owner_id == actor_id()
            )
        )
        else _missing()
    )


def _missing():
    from flask import abort

    abort(404)


def add_version(
    document: Document, upload: FileStorage, notes: str | None = None
) -> DocumentVersion:
    original = secure_filename(upload.filename or "document")
    suffix = Path(original).suffix.lower()
    content = upload.read()
    mime_type = upload.mimetype or "application/octet-stream"
    from app.storage.services import upload as upload_to_configured_storage

    stored = upload_to_configured_storage(original, mime_type, content)
    if stored is None:
        storage_name = f"{uuid4().hex}{suffix}"
        folder = Path(current_app.config["UPLOAD_FOLDER"])
        folder.mkdir(parents=True, exist_ok=True)
        (folder / storage_name).write_bytes(content)
        storage_provider = "local"
        external_url = None
    else:
        storage_name = stored.identifier
        storage_provider = "google_drive"
        external_url = stored.web_url or (
            f"https://drive.google.com/file/d/{stored.identifier}/view"
        )
    number = (
        db.session.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )
        or 0
    ) + 1
    version = DocumentVersion(
        document=document,
        version_number=number,
        original_filename=original,
        storage_name=storage_name,
        storage_provider=storage_provider,
        external_url=external_url,
        mime_type=mime_type,
        size_bytes=len(content),
        notes=notes,
    )
    db.session.add(version)
    db.session.commit()
    return version


def create_document(title, document_type, description, upload, notes=None):
    document = Document(
        title=title.strip(), document_type=document_type, description=description
    )
    db.session.add(document)
    db.session.flush()
    add_version(document, upload, notes)
    return document


def application_choices():
    rows = db.session.scalars(
        select(Application)
        .where(Application.owner_id == actor_id())
        .order_by(Application.updated_at.desc())
    )
    return [
        (a.id, f"{a.job_posting.title} · {a.job_posting.organization.name}")
        for a in rows
    ]


def attach_latest(document, application_id, purpose):
    application = db.session.scalar(
        select(Application).where(
            Application.id == application_id, Application.owner_id == actor_id()
        )
    )
    if application is None or not document.versions:
        raise ValueError("A valid application and document version are required.")
    existing = db.session.scalar(
        select(ApplicationDocument).where(
            ApplicationDocument.application_id == application.id,
            ApplicationDocument.document_version_id == document.versions[0].id,
        )
    )
    if existing is None:
        db.session.add(
            ApplicationDocument(
                application=application, version=document.versions[0], purpose=purpose
            )
        )
    db.session.commit()
