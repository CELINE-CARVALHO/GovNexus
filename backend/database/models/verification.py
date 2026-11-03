from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now_naive,
)


class FactVerification(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "fact_verifications"

    __table_args__ = (
        Index(
            "ix_fact_verifications_fact",
            "source_fact_id",
        ),
        Index(
            "ix_fact_verifications_status",
            "verification_status",
        ),
        Index(
            "ix_fact_verifications_reviewer",
            "reviewer_admin_id",
        ),
    )

    source_fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_facts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    reviewer_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_reference: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    supersedes_verification_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "fact_verifications.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    source_fact: Mapped[SourceFact] = relationship(
        "SourceFact",
    )

    reviewer: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        foreign_keys=[reviewer_admin_id],
    )

    supersedes: Mapped[FactVerification | None] = relationship(
        "FactVerification",
        remote_side="FactVerification.id",
        foreign_keys=[supersedes_verification_id],
    )


class ReviewTask(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "review_tasks"

    __table_args__ = (
        Index(
            "ix_review_tasks_status_priority",
            "status",
            "priority",
        ),
        Index(
            "ix_review_tasks_assigned",
            "assigned_to_admin_id",
        ),
        Index(
            "ix_review_tasks_fact",
            "source_fact_id",
        ),
    )

    source_fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_facts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False,
    )

    assigned_to_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolution: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    source_fact: Mapped[SourceFact] = relationship(
        "SourceFact",
    )

    assigned_admin: Mapped[AdminUser | None] = relationship(
        "AdminUser",
        foreign_keys=[assigned_to_admin_id],
    )
