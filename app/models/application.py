"""Application database model."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.auth.permissions import actor_id
from app.extensions import db
from app.utils.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.auth.models import User
    from app.models.activity import Activity
    from app.models.document import ApplicationDocument
    from app.models.job_posting import JobPosting
    from app.models.task import Task


class Application(db.Model):
    """One user's application to a shared job posting."""

    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "salary_requested IS NULL OR salary_requested > 0",
            name="ck_applications_salary_requested_positive",
        ),
        CheckConstraint(
            "offer_salary IS NULL OR offer_salary > 0",
            name="ck_applications_offer_salary_positive",
        ),
        UniqueConstraint(
            "owner_id", "job_posting_id", name="uq_applications_owner_job_posting"
        ),
        Index("ix_applications_status", "status"),
        Index("ix_applications_application_date", "application_date"),
        Index("ix_applications_interview_date", "interview_date"),
        Index("ix_applications_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        default=actor_id,
    )
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            create_constraint=True,
            name="application_status",
        ),
        nullable=False,
        default=ApplicationStatus.PLANNED,
    )
    source: Mapped[str | None] = mapped_column(String(100))
    resume_version: Mapped[str | None] = mapped_column(String(1000))
    cover_letter_version: Mapped[str | None] = mapped_column(String(1000))
    recruiter_name: Mapped[str | None] = mapped_column(String(200))
    recruiter_email: Mapped[str | None] = mapped_column(String(320))
    salary_requested: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    interview_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interview_location: Mapped[str | None] = mapped_column(String(300))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    offer_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    withdrawn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    job_posting: Mapped["JobPosting"] = relationship(
        back_populates="applications", lazy="joined"
    )
    owner: Mapped["User"] = relationship(back_populates="owned_applications")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="application", lazy="selectin"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="application", lazy="selectin"
    )
    document_links: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", lazy="selectin"
    )

    @validates("status")
    def validate_status(
        self, key: str, value: ApplicationStatus | str
    ) -> ApplicationStatus:
        """Normalize and constrain application statuses."""
        try:
            return ApplicationStatus(value)
        except ValueError as exc:
            raise ValueError("Invalid application status.") from exc

    def validate_business_rules(self) -> None:
        """Validate date ordering and positive monetary values."""
        if (
            self.application_date is not None
            and self.interview_date is not None
            and self.interview_date.date() < self.application_date
        ):
            raise ValueError("Interview date cannot precede application date.")
        if self.salary_requested is not None and self.salary_requested <= 0:
            raise ValueError("Salary requested must be positive.")
        if self.offer_salary is not None and self.offer_salary <= 0:
            raise ValueError("Offer salary must be positive.")

    def __repr__(self) -> str:
        return f"<Application job_posting_id={self.job_posting_id}>"
