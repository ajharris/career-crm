"""Contact database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from app.utils.enums import RelationshipStatus

if TYPE_CHECKING:
    from app.models.organization import Organization


class Contact(db.Model):
    """A person associated with exactly one organization."""

    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_organization_last_name", "organization_id", "last_name"),
        Index("ix_contacts_title", "title"),
        Index("ix_contacts_relationship_status", "relationship_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    relationship_status: Mapped[RelationshipStatus | None] = mapped_column(
        Enum(
            RelationshipStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            create_constraint=True,
            name="relationship_status",
        )
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
        back_populates="contacts", lazy="joined"
    )

    @validates("first_name", "last_name")
    def validate_required_name(self, key: str, value: str) -> str:
        """Require and normalize both parts of the contact's name."""
        if not isinstance(value, str) or not (normalized := value.strip()):
            label = key.replace("_", " ").title()
            raise ValueError(f"{label} is required.")
        return normalized

    @property
    def full_name(self) -> str:
        """Return the contact's display name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Contact {self.full_name}>"
