"""Skill matching and demand analytics."""

from flask_login import login_user

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


def test_matching_edge_cases_no_requirements_perfect_and_zero(app, user):
    from app.skills.services import job_match

    organization = Organization(
        name="Edges", created_by_id=user.id, updated_by_id=user.id
    )
    job = JobPosting(
        title="Edge Role",
        organization=organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.session.add(job)
    db.session.commit()
    with app.test_request_context():
        login_user(user)
        assert job_match(job)["percentage"] is None

        skill = Skill(
            name="Rust",
            category="programming_language",
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        requirement = JobSkill(job_posting=job, skill=skill, importance=5)
        db.session.add(requirement)
        db.session.commit()
        assert job_match(job)["percentage"] == 0

        db.session.add(
            UserSkill(user_id=user.id, skill=skill, proficiency="intermediate")
        )
        db.session.commit()
        assert job_match(job)["percentage"] == 100


def test_matching_is_deterministic_and_isolated_between_users(app, user, second_user):
    from app.skills.services import job_match

    organization = Organization(
        name="Isolation", created_by_id=user.id, updated_by_id=user.id
    )
    job = JobPosting(
        title="Two Skill Role",
        organization=organization,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    primary = Skill(
        name="Primary",
        category="other",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    secondary = Skill(
        name="Secondary",
        category="other",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.session.add_all([job, primary, secondary])
    db.session.flush()
    db.session.add_all(
        [
            JobSkill(job_posting=job, skill=primary, importance=5),
            JobSkill(job_posting=job, skill=secondary, importance=1),
        ]
    )
    db.session.flush()
    db.session.add_all(
        [
            UserSkill(user_id=user.id, skill=primary, proficiency="basic"),
            UserSkill(user_id=second_user.id, skill=secondary, proficiency="expert"),
        ]
    )
    db.session.commit()

    with app.test_request_context():
        login_user(user)
        strong = job_match(job)
        assert strong["percentage"] == 83
        assert job_match(job)["percentage"] == strong["percentage"]
    with app.test_request_context():
        login_user(second_user)
        weak = job_match(job)
        assert weak["percentage"] == 17
    assert strong["percentage"] > weak["percentage"]
