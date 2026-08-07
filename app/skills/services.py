"""Weighted skill matching and learning analysis."""

from sqlalchemy import func, select

from app.auth.permissions import actor_id, require_shared_editor
from app.extensions import db
from app.models.career_profile import JobSkill, Skill, UserSkill
from app.models.job_posting import JobPosting
from app.utils.enums import JobStatus


def skill_choices() -> list[tuple[int, str]]:
    return [
        (skill.id, f"{skill.name} · {skill.category.replace('_', ' ').title()}")
        for skill in db.session.scalars(select(Skill).order_by(Skill.name))
    ]


def add_job_skill(job: JobPosting, **values) -> JobSkill:
    require_shared_editor(job)
    skill = db.session.get(Skill, values["skill_id"])
    if skill is None:
        raise ValueError("A valid skill is required.")
    record = db.session.scalar(
        select(JobSkill).where(
            JobSkill.job_posting_id == job.id, JobSkill.skill_id == skill.id
        )
    )
    if record is None:
        record = JobSkill(job_posting_id=job.id, skill_id=skill.id)
        db.session.add(record)
    record.required = values.get("required", True)
    record.importance = values.get("importance", 3)
    record.notes = values.get("notes")
    db.session.commit()
    return record


def delete_job_skill(job: JobPosting, record_id: int) -> None:
    require_shared_editor(job)
    record = db.session.scalar(
        select(JobSkill).where(
            JobSkill.id == record_id, JobSkill.job_posting_id == job.id
        )
    )
    if record is None:
        raise ValueError("Job skill not found.")
    db.session.delete(record)
    db.session.commit()


def job_match(job: JobPosting) -> dict:
    """Return structured weighted match data for the current user."""
    requirements = list(
        db.session.scalars(
            select(JobSkill)
            .where(JobSkill.job_posting_id == job.id)
            .order_by(JobSkill.importance.desc(), JobSkill.id)
        )
    )
    user_skill_ids = set(
        db.session.scalars(
            select(UserSkill.skill_id).where(UserSkill.user_id == actor_id())
        )
    )
    total_weight = sum(item.importance for item in requirements)
    matched_weight = sum(
        item.importance for item in requirements if item.skill_id in user_skill_ids
    )
    matched = [item for item in requirements if item.skill_id in user_skill_ids]
    missing = [item for item in requirements if item.skill_id not in user_skill_ids]
    return {
        "percentage": (
            round(matched_weight / total_weight * 100) if total_weight else None
        ),
        "matched": matched,
        "missing": missing,
        "requirements": requirements,
    }


def skill_matrix() -> dict:
    """Return owned skills, global demand frequency, and learning suggestions."""
    owned = list(
        db.session.scalars(
            select(UserSkill)
            .where(UserSkill.user_id == actor_id())
            .order_by(UserSkill.proficiency.desc(), UserSkill.id)
        )
    )
    frequency_rows = db.session.execute(
        select(Skill, func.count(JobSkill.id))
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .join(JobPosting, JobPosting.id == JobSkill.job_posting_id)
        .where(JobPosting.status.not_in((JobStatus.CLOSED, JobStatus.SKIPPED)))
        .group_by(Skill.id)
        .order_by(func.count(JobSkill.id).desc(), Skill.name)
    ).all()
    owned_ids = {item.skill_id for item in owned}
    recommendations = [
        {"skill": skill, "frequency": count}
        for skill, count in frequency_rows
        if skill.id not in owned_ids
    ][:10]
    return {
        "owned": owned,
        "frequency": frequency_rows,
        "recommendations": recommendations,
    }
