"""add versioned documents

Revision ID: f12b3c4d5e6a
Revises: f11a2c3d4e5f
"""

from alembic import op
from app.extensions import db
import app.models  # noqa: F401

revision = "f12b3c4d5e6a"
down_revision = "f11a2c3d4e5f"
branch_labels = None
depends_on = None
TABLES = ("documents", "document_versions", "application_documents")


def upgrade():
    bind = op.get_bind()
    for name in TABLES:
        db.metadata.tables[name].create(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for name in reversed(TABLES):
        db.metadata.tables[name].drop(bind, checkfirst=True)
