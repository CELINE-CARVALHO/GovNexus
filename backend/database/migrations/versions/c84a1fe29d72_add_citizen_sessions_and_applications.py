"""Add citizen token invalidation and application tracking.

Revision ID: c84a1fe29d72
Revises: b91c83b4c9da
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c84a1fe29d72"
down_revision: Union[str, Sequence[str], None] = "b91c83b4c9da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_token_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_table(
        "citizen_applications",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("service_version_id", sa.Uuid(), nullable=False),
        sa.Column("reference_number", sa.String(length=255), nullable=True),
        sa.Column("application_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "status_source",
            sa.String(length=30),
            server_default="citizen_recorded",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("document_checklist", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"],
            name=op.f("fk_citizen_applications_service_id_services"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_version_id"], ["service_versions.id"],
            name=op.f("fk_citizen_applications_service_version_id_service_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_citizen_applications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_citizen_applications")),
    )
    op.create_index(
        "ix_citizen_applications_user_status",
        "citizen_applications",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_citizen_applications_service",
        "citizen_applications",
        ["service_id"],
    )
    op.create_table(
        "application_status_history",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column(
            "status_source",
            sa.String(length=30),
            server_default="citizen_recorded",
            nullable=False,
        ),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status_source = 'citizen_recorded'",
            name=op.f("ck_application_status_history_citizen_recorded_only"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["citizen_applications.id"],
            name=op.f("fk_application_status_history_application_id_citizen_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["users.id"],
            name=op.f("fk_application_status_history_changed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_status_history")),
    )
    op.create_index(
        "ix_application_status_history_application_time",
        "application_status_history",
        ["application_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_status_history_application_time",
        table_name="application_status_history",
    )
    op.drop_table("application_status_history")
    op.drop_index(
        "ix_citizen_applications_service",
        table_name="citizen_applications",
    )
    op.drop_index(
        "ix_citizen_applications_user_status",
        table_name="citizen_applications",
    )
    op.drop_table("citizen_applications")
    op.drop_column("users", "auth_token_version")
