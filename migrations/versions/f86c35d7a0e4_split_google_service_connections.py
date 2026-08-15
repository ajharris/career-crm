"""Split Google Drive and Gmail into independent connections.

Revision ID: f86c35d7a0e4
Revises: e75b24c6f9d3
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f86c35d7a0e4"
down_revision: str | None = "e75b24c6f9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("google_account_connections") as batch_op:
        batch_op.add_column(
            sa.Column("service", sa.String(length=20), server_default="drive", nullable=False)
        )
        batch_op.drop_constraint("uq_google_connection_user", type_="unique")
        batch_op.create_unique_constraint(
            "uq_google_connection_user_service", ["user_id", "service"]
        )


def downgrade() -> None:
    # A user may have separate Drive and Gmail rows. Keep Drive preferentially
    # before restoring the former one-row-per-user constraint.
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM google_account_connections WHERE service != 'drive'")
    )
    with op.batch_alter_table("google_account_connections") as batch_op:
        batch_op.drop_constraint("uq_google_connection_user_service", type_="unique")
        batch_op.create_unique_constraint("uq_google_connection_user", ["user_id"])
        batch_op.drop_column("service")
