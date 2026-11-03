from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class IngestionJob(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "ingestion_jobs"

    __table_args__ = (
        Index(
            "ix_ingestion_jobs_status_schedule",
            "status",
            "scheduled_at",
        ),
        Index(
            "ix_ingestion_jobs_source",
            "source_id",
        ),
        Index(
            "ix_ingestion_jobs_type",
            "job_type",
        ),
    )

    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=True,
    )

    triggered_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    job_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    worker_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    job_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    source: Mapped[Source | None] = relationship(
        "Source",
    )

    triggered_by_admin: Mapped[AdminUser | None] = relationship(
        "AdminUser",
    )

    logs: Mapped[list[BackgroundJobLog]] = relationship(
        "BackgroundJobLog",
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
        order_by="BackgroundJobLog.occurred_at",
    )


class BackgroundJobLog(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "background_job_logs"

    __table_args__ = (
        Index(
            "ix_background_job_logs_job_time",
            "ingestion_job_id",
            "occurred_at",
        ),
        Index(
            "ix_background_job_logs_level",
            "log_level",
        ),
    )

    ingestion_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )

    log_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    event: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    ingestion_job: Mapped[IngestionJob] = relationship(
        "IngestionJob",
        back_populates="logs",
    )
