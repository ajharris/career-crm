"""Job posting database model."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from app.utils.enums import EmploymentType, JobSource, JobStatus, WorkMode

if TYPE_CHECKING:
    from app.models.organization import Organization


def _enum_type(enum_class: type, name: str) -> Enum:
    """Build a consistently configured non-native enum column type."""
    return Enum(
        enum_class,
        values_callable=lambda enum: [item.value for item in enum],
        native_enum=False,
        create_constraint=True,
        name=name,
    )


class JobPosting(db.Model):
    """A specific employment opportunity at an organization."""

    __tablename__ = "job_postings"
    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 5", name="ck_job_postings_priority_range"
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_job_postings_salary_range",
        ),
        CheckConstraint(
            "date_posted IS NULL OR closing_date IS NULL "
            "OR date_posted <= closing_date",
            name="ck_job_postings_date_range",
        ),
        Index("ix_job_postings_organization_status", "organization_id", "status"),
        Index("ix_job_postings_closing_date", "closing_date"),
        Index("ix_job_postings_date_posted", "date_posted"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    department: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        _enum_type(EmploymentType, "employment_type")
    )
    work_mode: Mapped[WorkMode | None] = mapped_column(
        _enum_type(WorkMode, "work_mode")
    )
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    posting_url: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[JobSource | None] = mapped_column(
        _enum_type(JobSource, "job_source")
    )
    date_posted: Mapped[date | None] = mapped_column(Date)
    closing_date: Mapped[date | None] = mapped_column(Date)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    priority: Mapped[int] = mapped_column(nullable=False, default=3)
    status: Mapped[JobStatus] = mapped_column(
        _enum_type(JobStatus, "job_status"),
        nullable=False,
        default=JobStatus.DISCOVERED,
    )
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="job_postings", lazy="joined"
    )

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        """Require and normalize a job title."""
        if not isinstance(value, str) or not (normalized := value.strip()):
            raise ValueError("Job title is required.")
        return normalized

    @validates("priority")
    def validate_priority(self, key: str, value: int) -> int:
        """Keep priority within the supported range."""
        if not 1 <= value <= 5:
            raise ValueError("Priority must be between 1 and 5.")
        return value

    def validate_ranges(self) -> None:
        """Validate salary and posting date ranges."""
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        if (
            self.date_posted is not None
            and self.closing_date is not None
            and self.closing_date < self.date_posted
        ):
            raise ValueError("Closing date cannot precede posting date.")

    def __repr__(self) -> str:
        return f"<JobPosting {self.title}>"
