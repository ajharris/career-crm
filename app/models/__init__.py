"""Models implemented by the current application milestones."""

from app.models.activity import Activity
from app.models.application import Application
from app.models.career_profile import (
    CareerPriority,
    CareerProfile,
    Certification,
    Education,
    Industry,
    JobFamily,
    JobSkill,
    PortfolioItem,
    PreferredLocation,
    PreferredRole,
    Skill,
    UserAIProviderCredential,
    UserLanguage,
    UserSkill,
    WorkPreference,
)
from app.models.collaboration import CompanyReview, OrganizationNote
from app.models.contact import Contact
from app.models.dashboard_widget import DashboardWidget
from app.models.document import ApplicationDocument, Document, DocumentVersion
from app.models.job_posting import JobPosting
from app.models.notification import NotificationDismissal
from app.models.organization import Organization
from app.models.saved_search import SavedSearch
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
    "JobSkill",
    "PortfolioItem",
    "PreferredLocation",
    "PreferredRole",
    "Skill",
    "UserLanguage",
    "UserSkill",
    "UserAIProviderCredential",
    "WorkPreference",
    "DashboardWidget",
    "Document",
    "DocumentVersion",
    "ApplicationDocument",
    "JobPosting",
    "Organization",
    "SavedSearch",
    "NotificationDismissal",
    "OrganizationNote",
    "CompanyReview",
    "Task",
]
