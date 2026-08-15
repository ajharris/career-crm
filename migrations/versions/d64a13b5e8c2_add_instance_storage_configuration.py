"""Add instance storage configuration and remote document metadata.

Revision ID: d64a13b5e8c2
Revises: c53f02a4d7b1
"""

import sqlalchemy as sa
from alembic import op

revision: str = "d64a13b5e8c2"
down_revision: str | None = "c53f02a4d7b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "instance_storage_configuration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "provider", sa.String(length=30), server_default="local", nullable=False
        ),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("account_email", sa.String(length=320), nullable=True),
        sa.Column("folder_id", sa.String(length=255), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    existing = {column["name"] for column in sa.inspect(bind).get_columns("document_versions")}
    with op.batch_alter_table("document_versions") as batch_op:
        if "storage_provider" not in existing:
            batch_op.add_column(
                sa.Column(
                    "storage_provider", sa.String(length=30), server_default="local", nullable=False
                )
            )
        if "external_url" not in existing:
            batch_op.add_column(sa.Column("external_url", sa.String(length=1000)))


def downgrade() -> None:
    with op.batch_alter_table("document_versions") as batch_op:
        batch_op.drop_column("external_url")
        batch_op.drop_column("storage_provider")
    op.drop_table("instance_storage_configuration")
