"""add optional profile AI settings and encrypted user credentials

Revision ID: a31c4e7f9b02
Revises: f24a8b9c0d1e
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a31c4e7f9b02"
down_revision: str | None = "f24a8b9c0d1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    existing = {
        column["name"]
        for column in sa.inspect(connection).get_columns("career_profiles")
    }
    columns = [
        sa.Column(
            "profile_completeness", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "ai_assistance_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "ai_suggestions_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("preferred_ai_provider", sa.String(50)),
        sa.Column("preferred_ai_model", sa.String(100)),
        sa.Column(
            "reminder_interval",
            sa.String(20),
            nullable=False,
            server_default="one_week",
        ),
        sa.Column("reminder_dismissed_until", sa.DateTime(timezone=True)),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("career_profiles", column)

    op.create_table(
        "user_ai_provider_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(16), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "provider", name="uq_user_ai_provider_credential"
        ),
    )
    op.create_index(
        "ix_user_ai_provider_credentials_user_id",
        "user_ai_provider_credentials",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_ai_provider_credentials_user_id",
        table_name="user_ai_provider_credentials",
    )
    op.drop_table("user_ai_provider_credentials")
    op.drop_column("career_profiles", "reminder_dismissed_until")
    op.drop_column("career_profiles", "reminder_interval")
    op.drop_column("career_profiles", "preferred_ai_model")
    op.drop_column("career_profiles", "preferred_ai_provider")
    op.drop_column("career_profiles", "ai_suggestions_enabled")
    op.drop_column("career_profiles", "ai_assistance_enabled")
    op.drop_column("career_profiles", "profile_completeness")
