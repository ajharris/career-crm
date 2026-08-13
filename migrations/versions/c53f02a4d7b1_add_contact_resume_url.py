"""Add a Google Drive résumé link to contacts.

Revision ID: c53f02a4d7b1
Revises: b42e91d3f6a8
"""

import sqlalchemy as sa
from alembic import op

revision: str = "c53f02a4d7b1"
down_revision: str | None = "b42e91d3f6a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts", sa.Column("resume_url", sa.String(length=1000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("contacts", "resume_url")
