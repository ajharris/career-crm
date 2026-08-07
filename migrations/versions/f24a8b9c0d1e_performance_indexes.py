"""add query-path indexes

Revision ID: f24a8b9c0d1e
Revises: f22e7a8b9c0d
"""

from alembic import op

revision = "f24a8b9c0d1e"
down_revision = "f22e7a8b9c0d"
branch_labels = None
depends_on = None
INDEXES = (
    ("ix_tasks_owner_status_due", "tasks", ["owner_id", "status", "due_date"]),
    (
        "ix_applications_owner_status_date",
        "applications",
        ["owner_id", "status", "application_date"],
    ),
    ("ix_activities_owner_occurred", "activities", ["owner_id", "occurred_at"]),
    ("ix_jobs_status_closing", "job_postings", ["status", "closing_date"]),
)


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
