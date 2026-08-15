"""Add per-user Google account connections.

Revision ID: e75b24c6f9d3
Revises: d64a13b5e8c2
"""

import sqlalchemy as sa
from alembic import op

revision: str = "e75b24c6f9d3"
down_revision: str | None = "d64a13b5e8c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_account_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_email", sa.String(length=320), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("granted_scopes", sa.Text(), nullable=False),
        sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_google_connection_user"),
    )
    op.create_index(
        "ix_google_account_connections_user_id",
        "google_account_connections",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_google_account_connections_user_id",
        table_name="google_account_connections",
    )
    op.drop_table("google_account_connections")
