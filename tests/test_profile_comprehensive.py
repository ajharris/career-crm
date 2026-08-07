"""Career-profile normalization, transitions, constraints, and isolation."""

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    CareerPriority,
    CareerProfile,
    Industry,
    JobFamily,
    PortfolioItem,
    PreferredLocation,
    PreferredRole,
    UserSkill,
    WorkPreference,
)


def test_onboarding_interest_and_work_preference_steps_are_normalized(
    authenticated_client, user
):
    profile = db.session.scalar(
        db.select(CareerProfile).where(CareerProfile.user_id == user.id)
    )
    profile.onboarding_completed = False
    profile.onboarding_step = 4
    db.session.commit()

    response = authenticated_client.post(
        "/profile/onboarding/4",
        data={
            "preferred_roles": "Platform Engineer, Researcher, Platform Engineer",
            "industries": ["Software", "Research"],
            "job_families": ["Software Engineering"],
        },
    )
    assert response.location == "/profile/onboarding/5"
    assert {role.name for role in db.session.scalars(db.select(PreferredRole))} == {
        "Platform Engineer",
        "Researcher",
    }
    assert {item.name for item in profile.industries} == {"Software", "Research"}
    assert {item.name for item in profile.job_families} == {"Software Engineering"}

    response = authenticated_client.post(
        "/profile/onboarding/5",
        data={
            "remote": "y",
            "hybrid": "y",
            "full_time": "y",
            "contract": "y",
            "willing_to_relocate": "y",
            "city": "Toronto",
            "region": "Ontario",
            "country": "Canada",
        },
    )
    assert response.location == "/profile/onboarding/6"
    preferences = {
        (item.preference_type, item.value)
        for item in db.session.scalars(db.select(WorkPreference))
    }
    assert preferences == {
        ("work_mode", "remote"),
        ("work_mode", "hybrid"),
        ("employment_type", "full_time"),
        ("employment_type", "contract"),
    }
    location = db.session.scalar(db.select(PreferredLocation))
    assert (location.city, location.region, location.country) == (
        "Toronto",
        "Ontario",
        "Canada",
    )


def test_onboarding_strategy_completion_timestamp_and_resume(
    authenticated_client, user
):
    profile = user.career_profile
    profile.onboarding_completed = False
    profile.onboarding_step = 8
    db.session.commit()
    authenticated_client.post(
        "/profile/onboarding/8",
        data={
            "applications_per_week_target": 8,
            "interested_in_networking": "y",
            "interested_in_recruiter_outreach": "y",
        },
    )
    assert profile.applications_per_week_target == 8
    assert profile.interested_in_networking is True
    assert profile.onboarding_step == 9
    assert authenticated_client.get("/profile/onboarding").location.endswith(
        "/profile/onboarding/9"
    )

    authenticated_client.post("/profile/onboarding/9")
    assert profile.onboarding_completed is True
    assert profile.onboarding_completed_at is not None
    assert authenticated_client.get("/profile/onboarding").location == "/"


def test_profile_child_crud_for_certification_language_location_and_portfolio(
    authenticated_client,
):
    cases = [
        ("certification", {"name": "AWS Associate"}),
        ("language", {"language_name": "French", "proficiency": "professional"}),
        ("location", {"city": "Ottawa", "country": "Canada"}),
        (
            "portfolio",
            {
                "item_type": "GitHub",
                "title": "Career CRM",
                "url": "https://github.com/example/crm",
            },
        ),
    ]
    for kind, payload in cases:
        response = authenticated_client.post(f"/profile/{kind}/new", data=payload)
        assert response.status_code == 302

    item = db.session.scalar(db.select(PortfolioItem))
    response = authenticated_client.post(
        f"/profile/portfolio/{item.id}/edit",
        data={"item_type": "Open Source", "title": "Updated CRM"},
    )
    assert response.status_code == 302
    assert item.title == "Updated CRM"
    assert (
        authenticated_client.post(f"/profile/portfolio/{item.id}/delete").status_code
        == 302
    )
    assert db.session.get(PortfolioItem, item.id) is None


def test_profile_uniqueness_constraints_are_per_user(user, second_user, skills):
    db.session.add_all(
        [
            UserSkill(user_id=user.id, skill_id=skills[0].id, proficiency="advanced"),
            UserSkill(
                user_id=second_user.id,
                skill_id=skills[0].id,
                proficiency="basic",
            ),
            CareerPriority(user_id=user.id, factor="Compensation", weight=5),
            CareerPriority(user_id=second_user.id, factor="Compensation", weight=2),
        ]
    )
    db.session.commit()
    assert (
        db.session.scalar(
            db.select(db.func.count(UserSkill.id)).where(
                UserSkill.skill_id == skills[0].id
            )
        )
        == 2
    )

    db.session.add(
        UserSkill(user_id=user.id, skill_id=skills[0].id, proficiency="expert")
    )
    with __import__("pytest").raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_reference_taxonomies_are_shared_without_leaking_profile_associations(
    authenticated_client, second_authenticated_client, user, second_user
):
    industry = Industry(name="Quantum")
    family = JobFamily(name="Quantum Research")
    db.session.add_all([industry, family])
    db.session.commit()
    user.career_profile.industries.append(industry)
    user.career_profile.job_families.append(family)
    db.session.commit()

    response = second_authenticated_client.get("/profile")
    assert b"Quantum Research" not in response.data
    assert industry in user.career_profile.industries
    assert industry not in second_user.career_profile.industries
