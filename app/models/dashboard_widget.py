"""Persisted dashboard widget preferences."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class DashboardWidget(db.Model):
    """Visibility and display order for one dashboard widget."""

    __tablename__ = "dashboard_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    widget_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<DashboardWidget {self.widget_key}>"
