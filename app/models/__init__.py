"""Models implemented by the current application milestones."""

from app.models.activity import Activity
from app.models.application import Application
from app.models.contact import Contact
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
from app.models.dashboard_widget import DashboardWidget
from app.models.job_posting import JobPosting
from app.models.organization import Organization
from app.models.task import Task

__all__ = [
    "Activity",
    "Application",
    "Contact",
    "CareerProfile",
    "CareerPriority",
    "Certification",
    "Education",
    "Industry",
    "JobFamily",
    "PortfolioItem",
    "PreferredLocation",
    "PreferredRole",
    "Skill",
    "UserLanguage",
    "UserSkill",
    "WorkPreference",
    "DashboardWidget",
    "JobPosting",
    "Organization",
    "Task",
]
