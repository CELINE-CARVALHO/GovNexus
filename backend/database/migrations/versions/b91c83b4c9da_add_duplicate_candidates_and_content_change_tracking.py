"""add duplicate candidates and source content change tracking

Revision ID: b91c83b4c9da
Revises: 3f6b075e67e0
Create Date: 2026-11-05 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91c83b4c9da"
down_revision: Union[str, Sequence[str], None] = "3f6b075e67e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("content_changed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "fact_duplicate_candidates",
        sa.Column("source_fact_id", sa.Uuid(), nullable=False),
        sa.Column("duplicate_fact_id", sa.Uuid(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("review_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_fact_id"],
            ["source_facts.id"],
            name=op.f("fk_fact_duplicate_candidates_source_fact_id_source_facts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_fact_id"],
            ["source_facts.id"],
            name=op.f("fk_fact_duplicate_candidates_duplicate_fact_id_source_facts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_fact_duplicate_candidates_reviewed_by_admin_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fact_duplicate_candidates")),
        sa.UniqueConstraint(
            "source_fact_id",
            "duplicate_fact_id",
            "reason",
            name="uq_fact_duplicate_candidate",
        ),
    )
    op.create_index(
        op.f("ix_fact_duplicate_candidates_source_fact_id"),
        "fact_duplicate_candidates",
        ["source_fact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_duplicate_candidates_duplicate_fact_id"),
        "fact_duplicate_candidates",
        ["duplicate_fact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_duplicate_candidates_reviewed_by_admin_id"),
        "fact_duplicate_candidates",
        ["reviewed_by_admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_fact_duplicate_candidates_reviewed_by_admin_id"), table_name="fact_duplicate_candidates")
    op.drop_index(op.f("ix_fact_duplicate_candidates_duplicate_fact_id"), table_name="fact_duplicate_candidates")
    op.drop_index(op.f("ix_fact_duplicate_candidates_source_fact_id"), table_name="fact_duplicate_candidates")
    op.drop_table("fact_duplicate_candidates")
    op.drop_column("sources", "content_changed_at")
