"""Per-user external account connections."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.auth.models import User


class GoogleAccountConnection(db.Model):
    """Encrypted Google OAuth grant belonging to one Career CRM user."""

    __tablename__ = "google_account_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "service", name="uq_google_connection_user_service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service: Mapped[str] = mapped_column(String(20), nullable=False)
    account_email: Mapped[str] = mapped_column(String(320), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="google_connections")

    def has_scope(self, scope: str) -> bool:
        return scope in self.granted_scopes.split()
