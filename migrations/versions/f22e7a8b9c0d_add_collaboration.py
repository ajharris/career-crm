"""add collaboration records

Revision ID: f22e7a8b9c0d
Revises: f15d6e7a8b9c
"""
from alembic import op
from app.extensions import db
import app.models  # noqa:F401
revision="f22e7a8b9c0d";down_revision="f15d6e7a8b9c";branch_labels=None;depends_on=None
TABLES=("organization_notes","company_reviews")
def upgrade():
 bind=op.get_bind()
 for name in TABLES: db.metadata.tables[name].create(bind,checkfirst=True)
def downgrade():
 bind=op.get_bind()
 for name in reversed(TABLES): db.metadata.tables[name].drop(bind,checkfirst=True)
