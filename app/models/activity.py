"""Activity database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.auth.permissions import actor_id
from app.extensions import db
from app.utils.enums import ActivityDirection, ActivityType

if TYPE_CHECKING:
    from app.auth.models import User
    from app.models.application import Application
    from app.models.contact import Contact
    from app.models.job_posting import JobPosting
    from app.models.organization import Organization


class Activity(db.Model):
    """A completed interaction or event in the job-search timeline."""

    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_organization_occurred", "organization_id", "occurred_at"),
        Index("ix_activities_contact_occurred", "contact_id", "occurred_at"),
        Index("ix_activities_job_occurred", "job_posting_id", "occurred_at"),
        Index("ix_activities_application_occurred", "application_id", "occurred_at"),
        Index("ix_activities_type", "activity_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        default=actor_id,
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), index=True
    )
    job_posting_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_postings.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(
            ActivityType,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            create_constraint=True,
            name="activity_type",
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    direction: Mapped[ActivityDirection] = mapped_column(
        Enum(
            ActivityDirection,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            create_constraint=True,
            name="activity_direction",
        ),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    follow_up_needed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
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

    organization: Mapped["Organization | None"] = relationship(
        back_populates="activities"
    )
    owner: Mapped["User"] = relationship(back_populates="owned_activities")
    contact: Mapped["Contact | None"] = relationship(back_populates="activities")
    job_posting: Mapped["JobPosting | None"] = relationship(back_populates="activities")
    application: Mapped["Application | None"] = relationship(
        back_populates="activities"
    )

    @validates("activity_type")
    def validate_activity_type(
        self, key: str, value: ActivityType | str
    ) -> ActivityType:
        """Normalize and constrain activity types."""
        try:
            return ActivityType(value)
        except ValueError as exc:
            raise ValueError("Invalid activity type.") from exc

    @validates("direction")
    def validate_direction(
        self, key: str, value: ActivityDirection | str
    ) -> ActivityDirection:
        """Normalize and constrain activity directions."""
        try:
            return ActivityDirection(value)
        except ValueError as exc:
            raise ValueError("Invalid activity direction.") from exc

    def validate_relationship(self) -> None:
        """Require at least one related CRM entity for new and edited records."""
        if not any(
            (
                self.organization_id,
                self.contact_id,
                self.job_posting_id,
                self.application_id,
            )
        ):
            raise ValueError("At least one related entity is required.")

    def __repr__(self) -> str:
        return f"<Activity {self.activity_type.value} at {self.occurred_at}>"
