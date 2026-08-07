"""Normalized private career profile and shared reference models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

profile_industries = Table(
    "profile_industries",
    db.metadata,
    Column(
        "profile_id",
        ForeignKey("career_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "industry_id", ForeignKey("industries.id", ondelete="CASCADE"), primary_key=True
    ),
)
profile_job_families = Table(
    "profile_job_families",
    db.metadata,
    Column(
        "profile_id",
        ForeignKey("career_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "job_family_id",
        ForeignKey("job_families.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class CareerProfile(db.Model):
    __tablename__ = "career_profiles"
    __table_args__ = (
        CheckConstraint("years_of_experience IS NULL OR years_of_experience >= 0"),
        CheckConstraint(
            "applications_per_week_target IS NULL OR applications_per_week_target >= 0"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    highest_education_level: Mapped[str | None] = mapped_column(String(50))
    years_of_experience: Mapped[int | None]
    research_industry_preference: Mapped[str | None] = mapped_column(String(30))
    startup_enterprise_preference: Mapped[str | None] = mapped_column(String(30))
    management_interest: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    technical_leadership_preference: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    willing_to_relocate: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    willing_to_travel: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_target: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str] = mapped_column(
        String(3), default="CAD", nullable=False
    )
    security_clearance_status: Mapped[str | None] = mapped_column(String(50))
    work_authorization: Mapped[str | None] = mapped_column(String(100))
    applications_per_week_target: Mapped[int | None]
    interested_in_networking: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    interested_in_cold_outreach: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    interested_in_recruiter_outreach: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    interested_in_conferences: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    interested_in_government_roles: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    interested_in_academic_roles: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    onboarding_step: Mapped[int] = mapped_column(default=1, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user = relationship("User", back_populates="career_profile")
    industries = relationship("Industry", secondary=profile_industries)
    job_families = relationship("JobFamily", secondary=profile_job_families)


class Education(db.Model):
    __tablename__ = "education"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str | None] = mapped_column(String(80))
    degree_name: Mapped[str | None] = mapped_column(String(150))
    field_of_study: Mapped[str | None] = mapped_column(String(150))
    start_year: Mapped[int | None]
    graduation_year: Mapped[int | None]
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Certification(db.Model):
    __tablename__ = "certifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(200))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(150))
    credential_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)


class UserLanguage(db.Model):
    __tablename__ = "user_languages"
    __table_args__ = (
        UniqueConstraint("user_id", "language_name"),
        CheckConstraint(
            "proficiency IN ('basic', 'conversational', 'professional', "
            "'fluent', 'native_bilingual')"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[str] = mapped_column(String(30), nullable=False)


class Industry(db.Model):
    __tablename__ = "industries"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class JobFamily(db.Model):
    __tablename__ = "job_families"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class PreferredRole(db.Model):
    __tablename__ = "preferred_roles"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class PreferredLocation(db.Model):
    __tablename__ = "preferred_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), nullable=False)


class WorkPreference(db.Model):
    __tablename__ = "work_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "preference_type", "value"),
        CheckConstraint("preference_type IN ('work_mode', 'employment_type')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    preference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str] = mapped_column(String(40), nullable=False)


class Skill(db.Model):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserSkill(db.Model):
    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id"),
        CheckConstraint(
            "proficiency IN ('basic', 'intermediate', 'advanced', 'expert')"
        ),
        CheckConstraint("years_experience IS NULL OR years_experience >= 0"),
        CheckConstraint("interest_level IS NULL OR interest_level BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proficiency: Mapped[str] = mapped_column(String(30), nullable=False)
    years_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    interest_level: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)
    skill = relationship("Skill")


class JobSkill(db.Model):
    """A weighted skill requirement attached to a shared job posting."""

    __tablename__ = "job_skills"
    __table_args__ = (
        UniqueConstraint("job_posting_id", "skill_id"),
        CheckConstraint("importance BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    importance: Mapped[int] = mapped_column(default=3, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    skill = relationship("Skill")
    job_posting = relationship("JobPosting", back_populates="skill_requirements")


class CareerPriority(db.Model):
    __tablename__ = "career_priorities"
    __table_args__ = (
        UniqueConstraint("user_id", "factor"),
        CheckConstraint("weight BETWEEN 1 AND 5"),
        CheckConstraint(
            "factor IN ('Compensation', 'Stability', 'Interesting Work', "
            "'Career Growth', 'Work-Life Balance', 'Mission / Social Impact', "
            "'Prestige', 'Flexible Schedule', 'Technical Challenge', "
            "'Advancement', 'Location', 'Remote Flexibility')"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    factor: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class PortfolioItem(db.Model):
    __tablename__ = "portfolio_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('GitHub', 'LinkedIn', 'Personal Website', "
            "'Publication', 'Patent', 'Open Source', 'Portfolio Project', 'Other')"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
