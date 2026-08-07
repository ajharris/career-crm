"""add search and notification persistence

Revision ID: f15d6e7a8b9c
Revises: f13c4d5e6a7b
"""
from alembic import op
from app.extensions import db
import app.models  # noqa:F401
revision="f15d6e7a8b9c";down_revision="f13c4d5e6a7b";branch_labels=None;depends_on=None
def upgrade(): db.metadata.tables["notification_dismissals"].create(op.get_bind(),checkfirst=True)
def downgrade(): db.metadata.tables["notification_dismissals"].drop(op.get_bind(),checkfirst=True)
