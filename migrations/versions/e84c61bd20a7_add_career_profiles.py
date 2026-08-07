"""add normalized career profiles and onboarding

Revision ID: e84c61bd20a7
Revises: d73b42ce91f0
Create Date: 2026-08-07 00:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "e84c61bd20a7"
down_revision = "d73b42ce91f0"
branch_labels = None
depends_on = None

TABLES = (
    "career_profiles",
    "education",
    "certifications",
    "user_languages",
    "industries",
    "job_families",
    "preferred_roles",
    "preferred_locations",
    "work_preferences",
    "skills",
    "user_skills",
    "career_priorities",
    "portfolio_items",
    "profile_industries",
    "profile_job_families",
)

INDUSTRIES = (
    "Healthcare",
    "Medical Imaging",
    "Biotechnology",
    "Software",
    "AI/ML",
    "Government",
    "Aerospace",
    "Research",
)
JOB_FAMILIES = (
    "Software Engineering",
    "Data Science",
    "Research",
    "Scientific Computing",
    "Medical Physics",
    "Imaging Informatics",
    "Technical Operations",
)


def upgrade() -> None:
    """Create normalized tables and incomplete profiles for existing users."""
    from app.extensions import db
    import app.models  # noqa: F401

    connection = op.get_bind()
    for name in TABLES:
        db.metadata.tables[name].create(connection, checkfirst=True)
    for name in INDUSTRIES:
        connection.execute(
            sa.text("INSERT INTO industries (name) VALUES (:name)"), {"name": name}
        )
    for name in JOB_FAMILIES:
        connection.execute(
            sa.text("INSERT INTO job_families (name) VALUES (:name)"), {"name": name}
        )
    connection.execute(
        sa.text(
            "INSERT INTO career_profiles "
            "(user_id, management_interest, technical_leadership_preference, "
            "willing_to_relocate, willing_to_travel, salary_currency, "
            "interested_in_networking, interested_in_cold_outreach, "
            "interested_in_recruiter_outreach, interested_in_conferences, "
            "interested_in_government_roles, interested_in_academic_roles, "
            "onboarding_step, onboarding_completed) "
            "SELECT id, false, false, false, false, 'CAD', true, false, true, "
            "false, false, false, 1, false FROM users"
        )
    )


def downgrade() -> None:
    """Remove onboarding data without touching users or CRM records."""
    from app.extensions import db
    import app.models  # noqa: F401

    connection = op.get_bind()
    for name in reversed(TABLES):
        db.metadata.tables[name].drop(connection, checkfirst=True)
