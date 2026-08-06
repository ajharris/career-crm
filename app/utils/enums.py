# app/utils/enums.py

from enum import StrEnum


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
    DISCOVERED = "discovered"
    RESEARCHING = "researching"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    CLOSED = "closed"
    SKIPPED = "skipped"