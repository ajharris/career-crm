# app/models/organization.py

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.job_posting import JobPosting


class Organization(db.Model):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )

    organization_type: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    priority: Mapped[int] = mapped_column(default=3)
    notes: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    job_postings: Mapped[list["JobPosting"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )