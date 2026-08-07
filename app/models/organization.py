"""Organization database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.auth.permissions import actor_id
from app.extensions import db
from app.utils.enums import OrganizationType

if TYPE_CHECKING:
    from app.auth.models import User
    from app.models.activity import Activity
    from app.models.contact import Contact
    from app.models.job_posting import JobPosting
    from app.models.task import Task


class Organization(db.Model):
    """An employer, recruiter, agency, or other job-search organization."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 5",
            name="ck_organizations_priority_range",
        ),
        Index("ix_organizations_type", "organization_type"),
        Index("ix_organizations_location", "location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        default=actor_id,
    )
    updated_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        default=actor_id,
    )
    name: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    organization_type: Mapped[OrganizationType | None] = mapped_column(
        Enum(
            OrganizationType,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            create_constraint=True,
            name="organization_type",
        )
    )
    website: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    priority: Mapped[int] = mapped_column(nullable=False, default=3)
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
    created_by: Mapped["User"] = relationship(
        back_populates="organizations_created", foreign_keys=[created_by_id]
    )
    updated_by: Mapped["User"] = relationship(
        back_populates="organizations_updated", foreign_keys=[updated_by_id]
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    job_postings: Mapped[list["JobPosting"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="organization", lazy="selectin"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="organization", lazy="selectin"
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Require a non-empty, normalized organization name."""
        if not isinstance(value, str):
            raise ValueError("Organization name is required.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Organization name is required.")
        return normalized

    @validates("priority")
    def validate_priority(self, key: str, value: int) -> int:
        """Keep priorities within the supported one-to-five range."""
        if not 1 <= value <= 5:
            raise ValueError("Priority must be between 1 and 5.")
        return value

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"
