from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class ConversationSession(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "conversation_sessions"

    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR guest_session_id IS NOT NULL",
            name="conversation_has_owner",
        ),
        Index("ix_conversation_sessions_user", "user_id"),
        Index(
            "ix_conversation_sessions_guest",
            "guest_session_id",
        ),
        Index(
            "ix_conversation_sessions_status",
            "status",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    guest_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("guest_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        default="en",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utc_now_naive,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    user: Mapped[User | None] = relationship(
        "User",
        back_populates="conversations",
    )

    guest_session: Mapped[GuestSession | None] = relationship(
        "GuestSession",
        back_populates="conversations",
    )

    messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.message_index",
    )


class ConversationMessage(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "conversation_messages"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "message_index",
            name="uq_conversation_message_index",
        ),
        Index(
            "ix_conversation_messages_role",
            "role",
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conversation_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    message_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    message_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    conversation: Mapped[ConversationSession] = relationship(
        "ConversationSession",
        back_populates="messages",
    )


class SavedService(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "saved_services"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "service_id",
            name="uq_saved_service_user",
        ),
        Index("ix_saved_services_service", "service_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="saved_services",
    )

    service: Mapped[Service] = relationship(
        "Service",
    )
