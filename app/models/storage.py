"""Instance-wide external storage configuration."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class InstanceStorageConfiguration(db.Model):
    """Singleton storage selection shared by every account in an installation."""

    __tablename__ = "instance_storage_configuration"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, default="local", server_default="local"
    )
    encrypted_credentials: Mapped[str | None] = mapped_column(Text)
    account_email: Mapped[str | None] = mapped_column(String(320))
    folder_id: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
