from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    __table_args__ = (
        Index("ix_sources_authority_status", "authority_status"),
        Index("ix_sources_source_type", "source_type"),
        Index("ix_sources_active", "is_active"),
        Index("ix_sources_next_check", "next_check_at"),
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    url_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    publisher_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    authority_status: Mapped[str] = mapped_column(
        String(30),
        default="unverified",
        nullable=False,
    )

    jurisdiction_location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    language_code: Mapped[str | None] = mapped_column(
        ForeignKey("languages.code"),
        nullable=True,
    )

    retrieval_interval_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    next_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    content_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    jurisdiction: Mapped[Location | None] = relationship(
        "Location",
    )

    snapshots: Mapped[list[SourceSnapshot]] = relationship(
        "SourceSnapshot",
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="SourceSnapshot.fetched_at",
    )
