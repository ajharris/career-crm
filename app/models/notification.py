"""Local notification state."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.permissions import actor_id
from app.extensions import db


class NotificationDismissal(db.Model):
    __tablename__ = "notification_dismissals"
    __table_args__ = (UniqueConstraint("owner_id", "notification_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        default=actor_id,
        nullable=False,
        index=True,
    )
    notification_key: Mapped[str] = mapped_column(String(160), nullable=False)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
