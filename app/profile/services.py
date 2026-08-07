"""Career-profile persistence, completeness, and reminder operations."""

from datetime import UTC, datetime, timedelta

from flask import abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import actor_id
from app.extensions import db
from app.models.career_profile import (
    CareerPriority,
    CareerProfile,
    Certification,
    Education,
    Industry,
    JobFamily,
    PortfolioItem,
    PreferredLocation,
    PreferredRole,
    Skill,
    UserLanguage,
    UserSkill,
    WorkPreference,
)

COMPLETENESS_WEIGHTS = {
    "education": 15,
    "skills": 20,
    "career_interests": 15,
    "work_preferences": 15,
    "priorities": 10,
    "languages": 5,
    "portfolio": 10,
    "certifications": 5,
    "job_search_strategy": 5,
}


def get_profile() -> CareerProfile:
    profile = db.session.scalar(
        select(CareerProfile).where(CareerProfile.user_id == actor_id())
    )
    if profile is None:
        profile = CareerProfile(user_id=actor_id())
        db.session.add(profile)
        db.session.commit()
    return profile


def save_profile_step(profile: CareerProfile, values: dict, next_step: int) -> None:
    if profile.user_id != actor_id():
        abort(404)
    for key, value in values.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    profile.onboarding_step = max(profile.onboarding_step, next_step)
    db.session.commit()


def complete_onboarding(profile: CareerProfile) -> None:
    if profile.user_id != actor_id():
        abort(404)
    profile.onboarding_completed = True
    profile.onboarding_completed_at = datetime.now(UTC)
    profile.onboarding_step = 9
    db.session.commit()


def owned_records(model):
    return list(
        db.session.scalars(
            select(model).where(model.user_id == actor_id()).order_by(model.id)
        )
    )


def get_owned(model, record_id: int):
    record = db.session.scalar(
        select(model).where(model.id == record_id, model.user_id == actor_id())
    )
    if record is None:
        abort(404)
    return record


def create_education(values: dict) -> Education:
    record = Education(user_id=actor_id(), **values)
    db.session.add(record)
    db.session.commit()
    return record


def save_owned(model, values: dict, record_id: int | None = None):
    """Create or update one user-owned profile child."""
    record = get_owned(model, record_id) if record_id else model(user_id=actor_id())
    for key, value in values.items():
        setattr(record, key, value)
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("That entry already exists on your profile.") from exc
    return record


def save_skill(values: dict, record_id: int | None = None) -> UserSkill:
    name = values.pop("name").strip()
    category = values.pop("category")
    skill = db.session.scalar(select(Skill).where(Skill.name.ilike(name)))
    if skill is None:
        skill = Skill(
            name=name,
            category=category,
            created_by_id=actor_id(),
            updated_by_id=actor_id(),
        )
        db.session.add(skill)
        db.session.flush()
    record = (
        get_owned(UserSkill, record_id) if record_id else UserSkill(user_id=actor_id())
    )
    record.skill_id = skill.id
    for key, value in values.items():
        setattr(record, key, value)
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("That skill is already on your profile.") from exc
    return record


def save_interests(roles: str, industries: list[str], job_families: list[str]) -> None:
    """Persist normalized career-interest associations and user-entered roles."""
    db.session.query(PreferredRole).filter_by(user_id=actor_id()).delete()
    for name in {item.strip() for item in roles.split(",") if item.strip()}:
        db.session.add(PreferredRole(user_id=actor_id(), name=name))
    profile = get_profile()
    profile.industries = _references(Industry, industries)
    profile.job_families = _references(JobFamily, job_families)
    db.session.commit()


def _references(model, names: list[str]) -> list:
    records = []
    for name in names:
        record = db.session.scalar(select(model).where(model.name == name))
        if record is None:
            record = model(name=name)
            db.session.add(record)
        records.append(record)
    return records


def save_work_preferences(values: dict) -> None:
    profile = get_profile()
    profile.willing_to_relocate = values.pop("willing_to_relocate")
    profile.willing_to_travel = values.pop("willing_to_travel")
    location = {key: values.pop(key) for key in ("city", "region", "country")}
    db.session.query(WorkPreference).filter_by(user_id=actor_id()).delete()
    for kind, options in (
        ("work_mode", ("remote", "hybrid", "on_site")),
        (
            "employment_type",
            ("full_time", "part_time", "contract", "temporary", "internship"),
        ),
    ):
        for option in options:
            if values.get(option):
                db.session.add(
                    WorkPreference(
                        user_id=actor_id(), preference_type=kind, value=option
                    )
                )
    if location["country"]:
        db.session.add(PreferredLocation(user_id=actor_id(), **location))
    profile.onboarding_step = max(profile.onboarding_step, 6)
    db.session.commit()


def save_priority(values: dict) -> CareerPriority:
    record = db.session.scalar(
        select(CareerPriority).where(
            CareerPriority.user_id == actor_id(),
            CareerPriority.factor == values["factor"],
        )
    )
    if record is None:
        record = CareerPriority(user_id=actor_id(), factor=values["factor"])
        db.session.add(record)
    record.weight, record.notes = values["weight"], values.get("notes")
    db.session.commit()
    return record


def update_priority(values: dict, record_id: int | None = None) -> CareerPriority:
    """Create or edit a priority while preserving per-user factor uniqueness."""
    if record_id is None:
        return save_priority(values)
    record = get_owned(CareerPriority, record_id)
    record.factor = values["factor"]
    record.weight = values["weight"]
    record.notes = values.get("notes")
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("That priority is already on your profile.") from exc
    return record


def create_portfolio(values: dict) -> PortfolioItem:
    record = PortfolioItem(user_id=actor_id(), **values)
    db.session.add(record)
    db.session.commit()
    return record


def delete_owned(model, record_id: int) -> None:
    db.session.delete(get_owned(model, record_id))
    db.session.commit()


def profile_summary() -> dict:
    return {
        "roles": owned_records(PreferredRole)[:3],
        "skills": owned_records(UserSkill)[:5],
        "work_modes": list(
            db.session.scalars(
                select(WorkPreference).where(
                    WorkPreference.user_id == actor_id(),
                    WorkPreference.preference_type == "work_mode",
                )
            )
        ),
        "priorities": list(
            db.session.scalars(
                select(CareerPriority)
                .where(CareerPriority.user_id == actor_id())
                .order_by(CareerPriority.weight.desc())
                .limit(3)
            )
        ),
    }


def profile_completeness(profile: CareerProfile | None = None) -> dict:
    """Return structured completion data; persisted percentage is only a cache."""
    profile = profile or get_profile()
    present = {
        "education": bool(owned_records(Education)),
        "skills": bool(owned_records(UserSkill)),
        "career_interests": bool(
            owned_records(PreferredRole) or profile.industries or profile.job_families
        ),
        "work_preferences": bool(
            owned_records(WorkPreference) or owned_records(PreferredLocation)
        ),
        "priorities": bool(owned_records(CareerPriority)),
        "languages": bool(owned_records(UserLanguage)),
        "portfolio": bool(owned_records(PortfolioItem)),
        "certifications": bool(owned_records(Certification)),
        "job_search_strategy": profile.applications_per_week_target is not None,
    }
    percentage = sum(
        weight for section, weight in COMPLETENESS_WEIGHTS.items() if present[section]
    )
    profile.profile_completeness = percentage
    db.session.commit()
    return {
        "percentage": percentage,
        "sections": present,
        "next_sections": [
            section for section in COMPLETENESS_WEIGHTS if not present[section]
        ][:3],
    }


def set_reminder(interval: str) -> None:
    """Snooze or permanently dismiss the dashboard-only profile prompt."""
    delays = {
        "tomorrow": timedelta(days=1),
        "one_week": timedelta(weeks=1),
        "two_weeks": timedelta(weeks=2),
        "one_month": timedelta(days=30),
    }
    if interval not in {*delays, "never"}:
        raise ValueError("Unsupported reminder interval.")
    profile = get_profile()
    profile.reminder_interval = interval
    profile.reminder_dismissed_until = (
        None if interval == "never" else datetime.now(UTC) + delays[interval]
    )
    db.session.commit()


def should_show_profile_reminder(profile: CareerProfile) -> bool:
    if profile.onboarding_completed or profile.reminder_interval == "never":
        return False
    until = profile.reminder_dismissed_until
    if until is not None and until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return until is None or until <= datetime.now(UTC)
