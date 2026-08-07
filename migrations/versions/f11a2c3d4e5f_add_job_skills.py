"""add weighted job skill requirements

Revision ID: f11a2c3d4e5f
Revises: e84c61bd20a7
Create Date: 2026-08-07 02:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "f11a2c3d4e5f"
down_revision = "e84c61bd20a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_posting_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("job_posting_id", "skill_id"),
        sa.CheckConstraint("importance BETWEEN 1 AND 5"),
    )
    op.create_index("ix_job_skills_job_posting_id", "job_skills", ["job_posting_id"])
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])


def downgrade() -> None:
    op.drop_table("job_skills")
