"""Document routes."""

from pathlib import Path

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from sqlalchemy import select

from app.documents import bp
from app.documents.forms import AttachForm, DocumentForm, VersionForm
from app.documents.services import (
    add_version,
    application_choices,
    attach_latest,
    create_document,
    get_document,
    list_documents,
)
from app.extensions import db
from app.models.document import DocumentVersion


@bp.get("")
def index():
    return render_template("documents/index.html", documents=list_documents())


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = DocumentForm()
    if form.validate_on_submit():
        document = create_document(
            form.title.data,
            form.document_type.data,
            form.description.data,
            form.file.data,
            form.notes.data,
        )
        flash("Document uploaded.", "success")
        return redirect(url_for("documents.detail", document_id=document.id))
    return render_template("documents/form.html", form=form, title="Upload document")


@bp.route("/<int:document_id>", methods=["GET", "POST"])
def detail(document_id):
    document = get_document(document_id)
    form = VersionForm()
    attach_form = AttachForm()
    attach_form.application_id.choices = application_choices()
    if form.submit.data and form.validate_on_submit():
        add_version(document, form.file.data, form.notes.data)
        flash("Version added.", "success")
        return redirect(url_for("documents.detail", document_id=document.id))
    return render_template(
        "documents/detail.html", document=document, form=form, attach_form=attach_form
    )


@bp.post("/<int:document_id>/attach")
def attach(document_id):
    document = get_document(document_id)
    form = AttachForm()
    form.application_id.choices = application_choices()
    if form.validate_on_submit():
        attach_latest(document, form.application_id.data, form.purpose.data)
        flash("Document attached.", "success")
    return redirect(url_for("documents.detail", document_id=document.id))


@bp.get("/versions/<int:version_id>/download")
def download(version_id):
    version = db.session.scalar(
        select(DocumentVersion)
        .join(DocumentVersion.document)
        .where(
            DocumentVersion.id == version_id,
            DocumentVersion.document.has(
                owner_id=__import__(
                    "app.auth.permissions", fromlist=["actor_id"]
                ).actor_id()
            ),
        )
    )
    if version is None:
        return ("Not found", 404)
    return send_from_directory(
        Path(current_app.config["UPLOAD_FOLDER"]),
        version.storage_name,
        as_attachment=True,
        download_name=version.original_filename,
    )
