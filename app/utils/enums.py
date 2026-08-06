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
    PLANNED = "planned"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


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
