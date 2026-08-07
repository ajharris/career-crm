# app/utils/enums.py

from enum import StrEnum


class OrganizationType(StrEnum):
    """Supported organization categories."""

    HOSPITAL = "hospital"
    RESEARCH_INSTITUTE = "research_institute"
    HEALTH_TECH = "health_tech"
    MEDICAL_DEVICE = "medical_device"
    CRO = "cro"
    UNIVERSITY = "university"
    RECRUITER = "recruiter"
    GOVERNMENT = "government"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        labels = {
            self.CRO: "CRO",
            self.HEALTH_TECH: "Health Tech",
            self.MEDICAL_DEVICE: "Medical Device",
            self.RESEARCH_INSTITUTE: "Research Institute",
        }
        return labels.get(self, self.value.replace("_", " ").title())


class RelationshipStatus(StrEnum):
    """Current high-level relationship stage for a contact."""

    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    INTERVIEWING = "interviewing"
    LONG_TERM_CONNECTION = "long_term_connection"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        if self is self.LONG_TERM_CONNECTION:
            return "Long-term Connection"
        return self.value.title()


class ApplicationStatus(StrEnum):
    """Hiring-pipeline stage for an application."""

    PLANNED = "planned"
    PREPARING = "preparing"
    APPLIED = "applied"
    SCREENING = "screening"
    PHONE_INTERVIEW = "phone_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    PANEL_INTERVIEW = "panel_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()


class JobStatus(StrEnum):
    """Lifecycle state of a job posting."""

    DISCOVERED = "discovered"
    RESEARCHING = "researching"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    CLOSED = "closed"
    SKIPPED = "skipped"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()


class EmploymentType(StrEnum):
    """Supported employment arrangements."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()


class WorkMode(StrEnum):
    """Supported workplace arrangements."""

    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()


class JobSource(StrEnum):
    """Discovery channel for a job posting."""

    COMPANY_WEBSITE = "company_website"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    RECRUITER = "recruiter"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        if self is self.LINKEDIN:
            return "LinkedIn"
        return self.value.replace("_", " ").title()


class ActivityType(StrEnum):
    """Supported kinds of completed job-search interactions."""

    EMAIL = "email"
    LINKEDIN_MESSAGE = "linkedin_message"
    PHONE_CALL = "phone_call"
    INTERVIEW = "interview"
    NETWORKING = "networking"
    RECRUITER_CONTACT = "recruiter_contact"
    APPLICATION_SUBMITTED = "application_submitted"
    FOLLOW_UP = "follow_up"
    RESEARCH = "research"
    MEETING = "meeting"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        if self is self.LINKEDIN_MESSAGE:
            return "LinkedIn Message"
        return self.value.replace("_", " ").title()


class ActivityDirection(StrEnum):
    """Direction of an interaction relative to the user."""

    OUTBOUND = "outbound"
    INBOUND = "inbound"
    INTERNAL = "internal"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.title()


class TaskType(StrEnum):
    """Supported categories of actionable work."""

    FOLLOW_UP = "follow_up"
    APPLICATION = "application"
    INTERVIEW_PREPARATION = "interview_preparation"
    RESEARCH = "research"
    NETWORKING = "networking"
    DOCUMENT_PREPARATION = "document_preparation"
    THANK_YOU = "thank_you"
    PORTAL_CHECK = "portal_check"
    REMINDER = "reminder"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()


class TaskPriority(StrEnum):
    """Urgency level for a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.title()


class TaskStatus(StrEnum):
    """Workflow state for a task."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        """Return a human-readable label."""
        return self.value.replace("_", " ").title()
