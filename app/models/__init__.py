# app/models/__init__.py

from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.models.skill import Skill
from app.models.task import Task

__all__ = [
    "Activity",
    "Application",
    "Contact",
    "JobPosting",
    "Organization",
    "Skill",
    "Task",
]