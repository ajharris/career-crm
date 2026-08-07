"""add dashboard widgets

Revision ID: b14f8e7c9a21
Revises: 8ee3f8f631e0
Create Date: 2026-08-06 22:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "b14f8e7c9a21"
down_revision = "8ee3f8f631e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("widget_key", sa.String(length=50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("widget_key"),
    )


def downgrade() -> None:
    op.drop_table("dashboard_widgets")
