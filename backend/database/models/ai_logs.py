from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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
)


class RetrievalLog(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "retrieval_logs"

    __table_args__ = (
        Index(
            "ix_retrieval_logs_conversation",
            "conversation_id",
        ),
        Index(
            "ix_retrieval_logs_status",
            "retrieval_status",
        ),
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conversation_sessions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    retrieval_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    filters_applied: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    result_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    retrieval_status: Mapped[str] = mapped_column(
        String(30),
        default="completed",
        nullable=False,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    result_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    conversation: Mapped[ConversationSession | None] = relationship(
        "ConversationSession",
    )

    answers: Mapped[list[AnswerLog]] = relationship(
        "AnswerLog",
        back_populates="retrieval_log",
    )


class AnswerLog(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "answer_logs"

    __table_args__ = (
        Index(
            "ix_answer_logs_conversation",
            "conversation_id",
        ),
        Index(
            "ix_answer_logs_status",
            "answer_status",
        ),
        Index(
            "ix_answer_logs_model",
            "model_name",
        ),
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conversation_sessions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    assistant_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "conversation_messages.id",
            ondelete="SET NULL",
        ),
        unique=True,
        nullable=True,
    )

    retrieval_log_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "retrieval_logs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    model_provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    answer_status: Mapped[str] = mapped_column(
        String(30),
        default="completed",
        nullable=False,
    )

    grounding_status: Mapped[str] = mapped_column(
        String(30),
        default="not_evaluated",
        nullable=False,
    )

    response_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    answer_text_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    conversation: Mapped[ConversationSession | None] = relationship(
        "ConversationSession",
    )

    assistant_message: Mapped[ConversationMessage | None] = relationship(
        "ConversationMessage",
    )

    retrieval_log: Mapped[RetrievalLog | None] = relationship(
        "RetrievalLog",
        back_populates="answers",
    )

    citations: Mapped[list[AnswerCitation]] = relationship(
        "AnswerCitation",
        back_populates="answer",
        cascade="all, delete-orphan",
        order_by="AnswerCitation.citation_order",
    )


class AnswerCitation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "answer_citations"

    __table_args__ = (
        UniqueConstraint(
            "answer_id",
            "citation_order",
            name="uq_answer_citation_order",
        ),
        CheckConstraint(
            "(source_fact_id IS NOT NULL AND document_chunk_id IS NULL) "
            "OR (source_fact_id IS NULL AND document_chunk_id IS NOT NULL)",
            name="citation_has_one_evidence_target",
        ),
        Index(
            "ix_answer_citations_source_fact",
            "source_fact_id",
        ),
        Index(
            "ix_answer_citations_document_chunk",
            "document_chunk_id",
        ),
    )

    answer_id: Mapped[UUID] = mapped_column(
        ForeignKey("answer_logs.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_fact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "source_facts.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    document_chunk_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "document_chunks.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    citation_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    quoted_excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    evidence_locator: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    answer: Mapped[AnswerLog] = relationship(
        "AnswerLog",
        back_populates="citations",
    )

    source_fact: Mapped[SourceFact | None] = relationship(
        "SourceFact",
    )

    document_chunk: Mapped[DocumentChunk | None] = relationship(
        "DocumentChunk",
    )
