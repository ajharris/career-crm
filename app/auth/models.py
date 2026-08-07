"""Authentication and account database model."""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """A securely authenticated Career CRM account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    career_profile: Mapped["CareerProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    owned_contacts: Mapped[list["Contact"]] = relationship(back_populates="owner")
    owned_applications: Mapped[list["Application"]] = relationship(
        back_populates="owner"
    )
    owned_activities: Mapped[list["Activity"]] = relationship(back_populates="owner")
    owned_tasks: Mapped[list["Task"]] = relationship(back_populates="owner")
    organizations_created: Mapped[list["Organization"]] = relationship(
        back_populates="created_by", foreign_keys="Organization.created_by_id"
    )
    organizations_updated: Mapped[list["Organization"]] = relationship(
        back_populates="updated_by", foreign_keys="Organization.updated_by_id"
    )
    job_postings_created: Mapped[list["JobPosting"]] = relationship(
        back_populates="created_by", foreign_keys="JobPosting.created_by_id"
    )
    job_postings_updated: Mapped[list["JobPosting"]] = relationship(
        back_populates="updated_by", foreign_keys="JobPosting.updated_by_id"
    )

    @validates("email")
    def normalize_email(self, key: str, value: str) -> str:
        """Normalize email addresses before every persistence operation."""
        if not isinstance(value, str) or not (normalized := value.strip().lower()):
            raise ValueError("Email is required.")
        return normalized

    @validates("first_name", "last_name")
    def normalize_name(self, key: str, value: str) -> str:
        """Require clean account names."""
        if not isinstance(value, str) or not (normalized := value.strip()):
            raise ValueError(f"{key.replace('_', ' ').title()} is required.")
        return normalized

    def set_password(self, password: str) -> None:
        """Store a one-way password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Compare a candidate password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        """Return the user's display name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User {self.email}>"
