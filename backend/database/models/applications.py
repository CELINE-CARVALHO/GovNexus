from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now_naive,
)


class CitizenApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "citizen_applications"

    __table_args__ = (
        Index("ix_citizen_applications_user_status", "user_id", "status"),
        Index("ix_citizen_applications_service", "service_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reference_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="planning",
        nullable=False,
    )
    status_source: Mapped[str] = mapped_column(
        String(30),
        default="citizen_recorded",
        server_default=text("'citizen_recorded'"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_checklist: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="applications")
    service: Mapped[Service] = relationship("Service")
    service_version: Mapped[ServiceVersion] = relationship("ServiceVersion")
    status_history: Mapped[list[ApplicationStatusHistory]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at",
    )


class ApplicationStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "application_status_history"

    __table_args__ = (
        CheckConstraint(
            "status_source = 'citizen_recorded'",
            name="citizen_recorded_only",
        ),
        Index(
            "ix_application_status_history_application_time",
            "application_id",
            "changed_at",
        ),
    )

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("citizen_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    status_source: Mapped[str] = mapped_column(
        String(30),
        default="citizen_recorded",
        server_default=text("'citizen_recorded'"),
        nullable=False,
    )
    changed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    application: Mapped[CitizenApplication] = relationship(
        "CitizenApplication",
        back_populates="status_history",
    )
