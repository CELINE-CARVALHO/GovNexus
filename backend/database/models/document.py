from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
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
)


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    __table_args__ = (
        Index("ix_documents_source", "source_id"),
        Index("ix_documents_processing_status", "processing_status"),
        Index("ix_documents_service_version", "service_version_id"),
    )

    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    service_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("service_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    storage_uri: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    language_code: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=True,
    )

    processing_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    source: Mapped[Source | None] = relationship(
        "Source",
    )

    source_snapshot: Mapped[SourceSnapshot | None] = relationship(
        "SourceSnapshot",
        back_populates="documents",
    )

    service_version: Mapped[ServiceVersion | None] = relationship(
        "ServiceVersion",
        back_populates="documents",
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            "language_code",
            name="uq_document_chunk_language",
        ),
        Index(
            "ix_document_chunks_document",
            "document_id",
        ),
        Index(
            "ix_document_chunks_language",
            "language_code",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    text_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pinecone_vector_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="chunks",
    )

    translations: Mapped[list[DocumentChunkTranslation]] = relationship(
        "DocumentChunkTranslation",
        back_populates="document_chunk",
        cascade="all, delete-orphan",
    )


class DocumentChunkTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "document_chunk_translations"

    __table_args__ = (
        UniqueConstraint(
            "document_chunk_id",
            "language_code",
            name="uq_document_chunk_translation_language",
        ),
    )

    document_chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    translated_content: Mapped[str] = mapped_column(
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

    document_chunk: Mapped[DocumentChunk] = relationship(
        "DocumentChunk",
        back_populates="translations",
    )
