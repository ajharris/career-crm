"""Community visibility and moderation authorization."""

from app.extensions import db
from app.models import CompanyReview, OrganizationNote


def test_notes_are_shared_but_do_not_render_private_career_data(
    authenticated_client, second_authenticated_client, organization, second_user
):
    second_user.career_profile.work_authorization = "PRIVATE-AUTHORIZATION"
    note = OrganizationNote(
        organization_id=organization.id,
        author_id=second_user.id,
        body="Public company observation",
    )
    db.session.add(note)
    db.session.commit()
    response = authenticated_client.get(f"/community/organizations/{organization.id}")
    assert b"Public company observation" in response.data
    assert b"PRIVATE-AUTHORIZATION" not in response.data


def test_pending_and_rejected_reviews_are_not_public(
    authenticated_client, second_user, organization
):
    pending = CompanyReview(
        organization_id=organization.id,
        author_id=second_user.id,
        rating=3,
        body="Pending review text",
    )
    rejected = CompanyReview(
        organization_id=organization.id,
        author_id=second_user.id,
        rating=1,
        body="Rejected review text",
        moderation_status="rejected",
    )
    approved = CompanyReview(
        organization_id=organization.id,
        author_id=second_user.id,
        rating=5,
        body="Approved review text",
        moderation_status="approved",
    )
    db.session.add_all([pending, rejected, approved])
    db.session.commit()
    response = authenticated_client.get(f"/community/organizations/{organization.id}")
    assert b"Approved review text" in response.data
    assert b"Pending review text" not in response.data
    assert b"Rejected review text" not in response.data


def test_non_admin_cannot_moderate_review(
    authenticated_client, second_user, organization
):
    review = CompanyReview(
        organization_id=organization.id,
        author_id=second_user.id,
        rating=4,
        body="Needs moderation",
    )
    db.session.add(review)
    db.session.commit()
    response = authenticated_client.post(
        f"/community/reviews/{review.id}/moderate", data={"status": "approved"}
    )
    assert response.status_code == 403
    assert review.moderation_status == "pending"


def test_admin_can_approve_or_reject_but_invalid_status_is_ignored(
    admin_client, second_user, organization
):
    review = CompanyReview(
        organization_id=organization.id,
        author_id=second_user.id,
        rating=4,
        body="Moderate me",
    )
    db.session.add(review)
    db.session.commit()
    invalid = admin_client.post(
        f"/community/reviews/{review.id}/moderate", data={"status": "invalid"}
    )
    assert invalid.status_code == 302
    assert review.moderation_status == "pending"
    admin_client.post(
        f"/community/reviews/{review.id}/moderate", data={"status": "approved"}
    )
    assert review.moderation_status == "approved"
