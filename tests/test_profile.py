"""Onboarding, normalized profile, and profile-privacy tests."""

from app.auth.models import User
from app.extensions import db
from app.models.career_profile import (
    CareerPriority,
    CareerProfile,
    Certification,
    Education,
    PortfolioItem,
    PreferredLocation,
    Skill,
    UserLanguage,
    UserSkill,
)


PASSWORD = "correct horse battery staple"


def register(client, email="new@example.com"):
    return client.post(
        "/auth/register",
        data={
            "first_name": "New",
            "last_name": "Person",
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        },
    )


def test_registration_creates_one_incomplete_profile_and_redirects(client):
    register(client)
    user = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
    profile = db.session.scalar(
        db.select(CareerProfile).where(CareerProfile.user_id == user.id)
    )
    assert profile is not None and not profile.onboarding_completed
    response = client.get("/")
    assert response.status_code == 302
    assert response.location == "/profile/onboarding"


def test_progress_is_saved_and_resumed(client):
    register(client)
    response = client.post(
        "/profile/onboarding/1",
        data={
            "highest_education_level": "masters",
            "years_of_experience": 7,
            "management_interest": "y",
        },
    )
    assert response.location == "/profile/onboarding/2"
    profile = db.session.scalar(
        db.select(CareerProfile).join(User).where(User.email == "new@example.com")
    )
    assert profile.onboarding_step == 2
    assert profile.highest_education_level == "masters"
    assert client.get("/profile/onboarding").location == "/profile/onboarding/2"

    skipped = client.post("/profile/onboarding/2/skip")
    assert skipped.location == "/profile/onboarding/3"
    assert profile.onboarding_step == 3


def test_completion_unlocks_dashboard(client):
    register(client)
    response = client.post("/profile/onboarding/9", follow_redirects=True)
    assert response.status_code == 200
    assert b"Your career profile is ready" in response.data
    assert b"Dashboard" in response.data
    assert client.get("/profile/onboarding").location == "/"


def test_education_crud_and_cross_user_404(app, client):
    register(client)
    client.post("/profile/onboarding/9")
    response = client.post(
        "/profile/education/new",
        data={"institution": "Toronto", "degree_name": "MSc", "completed": "y"},
    )
    assert response.status_code == 302
    education = db.session.scalar(
        db.select(Education).where(Education.institution == "Toronto")
    )
    response = client.post(
        f"/profile/education/{education.id}/edit",
        data={"institution": "University of Toronto", "degree_name": "MSc"},
    )
    assert response.status_code == 302

    other = app.test_client()
    register(other, "other@example.com")
    assert other.get(f"/profile/education/{education.id}/edit").status_code == 404
    assert other.post(f"/profile/education/{education.id}/delete").status_code == 404


def test_priority_upsert_and_skill_duplicate_validation(client):
    register(client)
    client.post(
        "/profile/onboarding/6",
        data={"factor": "Compensation", "weight": 5},
    )
    client.post(
        "/profile/onboarding/6",
        data={"factor": "Compensation", "weight": 3},
    )
    from app.models.career_profile import CareerPriority, UserSkill

    priorities = db.session.scalars(db.select(CareerPriority)).all()
    assert len(priorities) == 1 and priorities[0].weight == 3
    first = client.post(
        "/profile/onboarding/3",
        data={"name": "Python", "category": "programming_language", "proficiency": "advanced"},
    )
    duplicate = client.post(
        "/profile/onboarding/3",
        data={"name": "Python", "category": "programming_language", "proficiency": "expert"},
    )
    assert first.status_code == 302
    assert b"already on your profile" in duplicate.data
    assert db.session.scalar(db.select(db.func.count(UserSkill.id))) == 1


def test_all_private_child_edit_routes_reject_another_user(app, client):
    register(client)
    owner = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
    skill = Skill(
        name="Private mapping",
        category="other",
        created_by_id=owner.id,
        updated_by_id=owner.id,
    )
    db.session.add(skill)
    db.session.flush()
    records = {
        "education": Education(user_id=owner.id, institution="Secret School"),
        "certification": Certification(user_id=owner.id, name="Secret Cert"),
        "language": UserLanguage(
            user_id=owner.id, language_name="Secret", proficiency="basic"
        ),
        "skill": UserSkill(
            user_id=owner.id, skill_id=skill.id, proficiency="basic"
        ),
        "priority": CareerPriority(
            user_id=owner.id, factor="Stability", weight=4
        ),
        "portfolio": PortfolioItem(
            user_id=owner.id, item_type="Other", title="Secret Work"
        ),
        "location": PreferredLocation(user_id=owner.id, country="Canada"),
    }
    db.session.add_all(records.values())
    db.session.commit()

    other = app.test_client()
    register(other, "other@example.com")
    for kind, record in records.items():
        assert other.get(f"/profile/{kind}/{record.id}/edit").status_code == 404
        assert other.post(f"/profile/{kind}/{record.id}/delete").status_code == 404


def test_completed_profile_sections_remain_editable(client):
    register(client)
    client.post("/profile/onboarding/9")
    assert client.get("/profile/onboarding/1").status_code == 200
    response = client.post(
        "/profile/onboarding/1",
        data={"highest_education_level": "doctorate", "years_of_experience": 8},
    )
    assert response.location == "/profile/onboarding/2"
