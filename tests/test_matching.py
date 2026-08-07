"""Skill matching and demand analytics."""

from app.extensions import db
from app.models import JobPosting, JobSkill, Organization, Skill, UserSkill


def _job_and_skills(user):
    organization = Organization(
        name="Matching Inc", created_by_id=user.id, updated_by_id=user.id
    )
    job = JobPosting(
        title="Engineer",
        organization=organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    python = Skill(
        name="Python",
        category="programming",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    sql = Skill(
        name="SQL", category="database", created_by_id=user.id, updated_by_id=user.id
    )
    db.session.add_all([job, python, sql])
    db.session.flush()
    db.session.add_all(
        [
            JobSkill(job_posting=job, skill=python, importance=5),
            JobSkill(job_posting=job, skill=sql, importance=3),
            UserSkill(user_id=user.id, skill=python, proficiency="advanced"),
        ]
    )
    db.session.commit()
    return job


def test_weighted_job_match(app, user):
    from app.skills.services import job_match

    with app.test_request_context():
        job = _job_and_skills(user)
        result = job_match(job)
    assert result["percentage"] == 62
    assert [item.skill.name for item in result["matched"]] == ["Python"]
    assert [item.skill.name for item in result["missing"]] == ["SQL"]


def test_skill_matrix_recommends_frequent_gap(app, user):
    from app.skills.services import skill_matrix

    with app.test_request_context():
        _job_and_skills(user)
        result = skill_matrix()
    assert result["owned"][0].skill.name == "Python"
    assert result["recommendations"][0]["skill"].name == "SQL"


def test_skills_pages(authenticated_client, user):
    job = _job_and_skills(user)
    assert authenticated_client.get("/skills").status_code == 200
    response = authenticated_client.get(f"/jobs/{job.id}")
    assert b"62%" in response.data
    assert authenticated_client.get(f"/skills/jobs/{job.id}").status_code == 200
