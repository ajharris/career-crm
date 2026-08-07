from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from app.collaboration import bp
from app.extensions import db
from app.models import CompanyReview, Organization, OrganizationNote


@bp.route("/organizations/<int:organization_id>", methods=["GET", "POST"])
def organization(organization_id):
    organization = db.get_or_404(Organization, organization_id)
    if request.method == "POST":
        kind = request.form.get("kind")
        body = request.form.get("body", "").strip()
        if body and kind == "note":
            db.session.add(OrganizationNote(organization_id=organization.id, body=body))
        elif body and kind == "review":
            db.session.add(
                CompanyReview(
                    organization_id=organization.id,
                    body=body,
                    rating=max(1, min(5, request.form.get("rating", 3, type=int))),
                )
            )
        db.session.commit()
        flash("Contribution submitted.", "success")
        return redirect(
            url_for("collaboration.organization", organization_id=organization.id)
        )
    notes = list(
        db.session.scalars(
            select(OrganizationNote)
            .where(OrganizationNote.organization_id == organization.id)
            .order_by(OrganizationNote.created_at.desc())
        )
    )
    reviews = list(
        db.session.scalars(
            select(CompanyReview)
            .where(
                CompanyReview.organization_id == organization.id,
                CompanyReview.moderation_status == "approved",
            )
            .order_by(CompanyReview.created_at.desc())
        )
    )
    pending = (
        list(
            db.session.scalars(
                select(CompanyReview).where(
                    CompanyReview.moderation_status == "pending"
                )
            )
        )
        if current_user.is_admin
        else []
    )
    return render_template(
        "collaboration/organization.html",
        organization=organization,
        notes=notes,
        reviews=reviews,
        pending=pending,
    )


@bp.post("/reviews/<int:review_id>/moderate")
def moderate(review_id):
    if not current_user.is_admin:
        abort(403)
    review = db.get_or_404(CompanyReview, review_id)
    status = request.form.get("status")
    if status in ("approved", "rejected"):
        review.moderation_status = status
        db.session.commit()
    return redirect(
        url_for("collaboration.organization", organization_id=review.organization_id)
    )
