"""Add an external profile page URL to contacts.

Revision ID: b42e91d3f6a8
Revises: a31c4e7f9b02
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b42e91d3f6a8"
down_revision: str | None = "a31c4e7f9b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts", sa.Column("profile_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("contacts", "profile_url")
