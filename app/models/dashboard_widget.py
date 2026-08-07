"""Persisted dashboard widget preferences."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.permissions import actor_id
from app.extensions import db


class DashboardWidget(db.Model):
    """Visibility and display order for one dashboard widget."""

    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "widget_key", name="uq_dashboard_widget_owner_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        default=actor_id,
    )
    widget_key: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    owner = relationship("User")

    def __repr__(self) -> str:
        return f"<DashboardWidget {self.widget_key}>"
