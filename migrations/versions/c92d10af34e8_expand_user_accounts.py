"""expand user accounts

Revision ID: c92d10af34e8
Revises: 3fa1dda11764
Create Date: 2026-08-06 23:15:00
"""

import sqlalchemy as sa
from alembic import op

revision = "c92d10af34e8"
down_revision = "3fa1dda11764"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add profile, security, and account lifecycle columns safely."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("first_name", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("last_name", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_active", sa.Boolean(), server_default=sa.true(), nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_admin", sa.Boolean(), server_default=sa.false(), nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "email_verified",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.execute(sa.text("UPDATE users SET first_name = '', last_name = ''"))
    op.execute(sa.text("UPDATE users SET email = lower(trim(email))"))
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "first_name", existing_type=sa.String(100), nullable=False
        )
        batch_op.alter_column("last_name", existing_type=sa.String(100), nullable=False)


def downgrade() -> None:
    """Restore the original placeholder user table shape."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("is_admin")
        batch_op.drop_column("is_active")
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
