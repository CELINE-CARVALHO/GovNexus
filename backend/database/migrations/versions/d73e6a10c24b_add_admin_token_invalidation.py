"""Add administrator token invalidation.

Revision ID: d73e6a10c24b
Revises: c84a1fe29d72
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d73e6a10c24b"
down_revision: Union[str, Sequence[str], None] = "c84a1fe29d72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column(
            "auth_token_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_users", "auth_token_version")
