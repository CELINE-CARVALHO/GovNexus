from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now_naive,
)


class SourceSnapshot(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "source_snapshots"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "content_hash",
            name="uq_source_snapshot_hash",
        ),
        Index(
            "ix_source_snapshots_fetched_at",
            "fetched_at",
        ),
        Index(
            "ix_source_snapshots_extraction_status",
            "extraction_status",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    storage_uri: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    source: Mapped[Source] = relationship(
        "Source",
        back_populates="snapshots",
    )

    facts: Mapped[list[SourceFact]] = relationship(
        "SourceFact",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="source_snapshot",
    )


class SourceFact(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "source_facts"

    __table_args__ = (
        Index(
            "ix_source_facts_snapshot",
            "source_snapshot_id",
        ),
        Index(
            "ix_source_facts_type",
            "fact_type",
        ),
        Index(
            "ix_source_facts_extraction_status",
            "extraction_status",
        ),
    )

    source_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fact_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    fact_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    value_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    evidence_locator: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extraction_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    snapshot: Mapped[SourceSnapshot] = relationship(
        "SourceSnapshot",
        back_populates="facts",
    )

    translations: Mapped[list[SourceFactTranslation]] = relationship(
        "SourceFactTranslation",
        back_populates="source_fact",
        cascade="all, delete-orphan",
    )

    service_links: Mapped[list[ServiceFactLink]] = relationship(
        "ServiceFactLink",
        back_populates="source_fact",
        cascade="all, delete-orphan",
    )


class SourceFactTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "source_fact_translations"

    __table_args__ = (
        UniqueConstraint(
            "source_fact_id",
            "language_code",
            name="uq_source_fact_translation_language",
        ),
    )

    source_fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_facts.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    translated_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    translation_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    is_human_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    source_fact: Mapped[SourceFact] = relationship(
        "SourceFact",
        back_populates="translations",
    )


class ServiceFactLink(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "service_fact_links"

    __table_args__ = (
        UniqueConstraint(
            "service_version_id",
            "source_fact_id",
            name="uq_service_fact_link",
        ),
        Index(
            "ix_service_fact_links_fact",
            "source_fact_id",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    source_fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_facts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50),
        default="supports",
        nullable=False,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="fact_links",
    )

    source_fact: Mapped[SourceFact] = relationship(
        "SourceFact",
        back_populates="service_links",
    )
