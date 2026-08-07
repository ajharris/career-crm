"""add saved searches

Revision ID: f13c4d5e6a7b
Revises: f12b3c4d5e6a
"""
from alembic import op
from app.extensions import db
import app.models  # noqa: F401
revision="f13c4d5e6a7b"; down_revision="f12b3c4d5e6a"; branch_labels=None; depends_on=None
def upgrade(): db.metadata.tables["saved_searches"].create(op.get_bind(),checkfirst=True)
def downgrade(): db.metadata.tables["saved_searches"].drop(op.get_bind(),checkfirst=True)
