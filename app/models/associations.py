# app/models/associations.py

from sqlalchemy import Column, ForeignKey, Table

from app.extensions import db

job_posting_skills = Table(
    "job_posting_skills",
    db.metadata,
    Column(
        "job_posting_id",
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
