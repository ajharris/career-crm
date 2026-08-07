"""Task database model."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.auth.permissions import actor_id
from app.extensions import db
from app.utils.enums import TaskPriority, TaskStatus, TaskType

if TYPE_CHECKING:
    from app.auth.models import User
    from app.models.application import Application
    from app.models.contact import Contact
    from app.models.job_posting import JobPosting
    from app.models.organization import Organization


def _enum_type(enum_class: type, name: str) -> Enum:
    return Enum(
        enum_class,
        values_callable=lambda enum: [item.value for item in enum],
        native_enum=False,
        create_constraint=True,
        name=name,
    )


class Task(db.Model):
    """An actionable item that may optionally relate to CRM entities."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status_due_date", "status", "due_date"),
        Index("ix_tasks_organization_status", "organization_id", "status"),
        Index("ix_tasks_contact_status", "contact_id", "status"),
        Index("ix_tasks_job_status", "job_posting_id", "status"),
        Index("ix_tasks_application_status", "application_id", "status"),
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
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[TaskType] = mapped_column(
        _enum_type(TaskType, "task_type"), nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        _enum_type(TaskPriority, "task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    status: Mapped[TaskStatus] = mapped_column(
        _enum_type(TaskStatus, "task_status"),
        nullable=False,
        default=TaskStatus.OPEN,
    )
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_time: Mapped[time | None] = mapped_column(Time)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization | None"] = relationship(back_populates="tasks")
    owner: Mapped["User"] = relationship(back_populates="owned_tasks")
    contact: Mapped["Contact | None"] = relationship(back_populates="tasks")
    job_posting: Mapped["JobPosting | None"] = relationship(back_populates="tasks")
    application: Mapped["Application | None"] = relationship(back_populates="tasks")

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        """Require and normalize a task title."""
        if not isinstance(value, str) or not (normalized := value.strip()):
            raise ValueError("Task title is required.")
        return normalized

    @validates("task_type")
    def validate_task_type(self, key: str, value: TaskType | str) -> TaskType:
        return self._validated_enum(TaskType, value, "task type")

    @validates("priority")
    def validate_priority(self, key: str, value: TaskPriority | str) -> TaskPriority:
        return self._validated_enum(TaskPriority, value, "task priority")

    @validates("status")
    def validate_status(self, key: str, value: TaskStatus | str) -> TaskStatus:
        return self._validated_enum(TaskStatus, value, "task status")

    @property
    def is_overdue(self) -> bool:
        """Return whether this actionable task is past its due date."""
        return (
            self.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
            and self.due_date is not None
            and self.due_date < date.today()
        )

    @staticmethod
    def _validated_enum(enum_class: type, value, label: str):
        try:
            return enum_class(value)
        except ValueError as exc:
            raise ValueError(f"Invalid {label}.") from exc

    def __repr__(self) -> str:
        return f"<Task {self.title}>"
