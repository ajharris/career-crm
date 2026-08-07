"""add multi-user ownership and shared audit fields

Revision ID: d73b42ce91f0
Revises: c92d10af34e8
Create Date: 2026-08-06 23:45:00
"""

import sqlalchemy as sa
from alembic import op

revision = "d73b42ce91f0"
down_revision = "c92d10af34e8"
branch_labels = None
depends_on = None

PRIVATE_TABLES = ("contacts", "applications", "activities", "tasks")
SHARED_TABLES = ("organizations", "job_postings")


def upgrade() -> None:
    """Add ownership columns and safely attribute single-user legacy data."""
    connection = op.get_bind()
    widget_unique_name = (
        next(
            (
                constraint["name"]
                for constraint in sa.inspect(connection).get_unique_constraints(
                    "dashboard_widgets"
                )
                if constraint.get("column_names") == ["widget_key"]
            ),
            None,
        )
        or "uq_dashboard_widgets_widget_key"
    )
    user_ids = list(
        connection.execute(sa.text("SELECT id FROM users ORDER BY id")).scalars()
    )
    data_tables = (*PRIVATE_TABLES, *SHARED_TABLES, "dashboard_widgets")
    has_legacy_data = any(
        connection.scalar(sa.text(f"SELECT count(*) FROM {table}"))
        for table in data_tables
    )
    if len(user_ids) != 1 and has_legacy_data:
        raise RuntimeError(
            "Cannot infer ownership with zero or multiple users and existing CRM data. "
            "Assign ownership explicitly before running this migration."
        )

    for table in PRIVATE_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_owner_id_users",
                "users",
                ["owner_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(f"ix_{table}_owner_id", ["owner_id"])

    for table in SHARED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            for field in ("created_by_id", "updated_by_id"):
                batch_op.add_column(sa.Column(field, sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    f"fk_{table}_{field}_users",
                    "users",
                    [field],
                    ["id"],
                    ondelete="RESTRICT",
                )
                batch_op.create_index(f"ix_{table}_{field}", [field])

    with op.batch_alter_table(
        "dashboard_widgets",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_dashboard_widgets_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_dashboard_widgets_owner_id", ["owner_id"])

    if len(user_ids) == 1:
        user_id = user_ids[0]
        for table in PRIVATE_TABLES:
            connection.execute(
                sa.text(f"UPDATE {table} SET owner_id = :user_id"),
                {"user_id": user_id},
            )
        for table in SHARED_TABLES:
            connection.execute(
                sa.text(
                    f"UPDATE {table} SET created_by_id = :user_id, "
                    "updated_by_id = :user_id"
                ),
                {"user_id": user_id},
            )
        connection.execute(
            sa.text("UPDATE dashboard_widgets SET owner_id = :user_id"),
            {"user_id": user_id},
        )
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_constraint("uq_applications_job_posting_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_applications_owner_job_posting", ["owner_id", "job_posting_id"]
        )
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_constraint(widget_unique_name, type_="unique")
        batch_op.create_unique_constraint(
            "uq_dashboard_widget_owner_key", ["owner_id", "widget_key"]
        )

    for table in PRIVATE_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "owner_id", existing_type=sa.Integer(), nullable=False
            )
    for table in SHARED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "created_by_id", existing_type=sa.Integer(), nullable=False
            )
            batch_op.alter_column(
                "updated_by_id", existing_type=sa.Integer(), nullable=False
            )
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.alter_column("owner_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    """Remove ownership fields and restore globally unique applications/widgets."""
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_constraint("uq_dashboard_widget_owner_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_dashboard_widgets_widget_key", ["widget_key"]
        )
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_constraint("uq_applications_owner_job_posting", type_="unique")
        batch_op.create_unique_constraint(
            "uq_applications_job_posting_id", ["job_posting_id"]
        )
    with op.batch_alter_table("dashboard_widgets") as batch_op:
        batch_op.drop_index("ix_dashboard_widgets_owner_id")
        batch_op.drop_constraint(
            "fk_dashboard_widgets_owner_id_users", type_="foreignkey"
        )
        batch_op.drop_column("owner_id")
    for table in SHARED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            for field in ("updated_by_id", "created_by_id"):
                batch_op.drop_index(f"ix_{table}_{field}")
                batch_op.drop_constraint(
                    f"fk_{table}_{field}_users", type_="foreignkey"
                )
                batch_op.drop_column(field)
    for table in PRIVATE_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_owner_id")
            batch_op.drop_constraint(f"fk_{table}_owner_id_users", type_="foreignkey")
            batch_op.drop_column("owner_id")
