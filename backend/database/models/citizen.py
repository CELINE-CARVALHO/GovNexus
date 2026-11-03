from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
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


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_status", "account_status"),
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        unique=True,
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    account_status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    preferred_language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        default="en",
        nullable=False,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    contexts: Mapped[list[UserContext]] = relationship(
        "UserContext",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    guest_sessions: Mapped[list[GuestSession]] = relationship(
        "GuestSession",
        back_populates="claimed_by_user",
    )

    conversations: Mapped[list[ConversationSession]] = relationship(
        "ConversationSession",
        back_populates="user",
    )

    saved_services: Mapped[list[SavedService]] = relationship(
        "SavedService",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    profile_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="profile",
    )

    location: Mapped[Location | None] = relationship(
        "Location",
    )


class GuestSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "guest_sessions"

    __table_args__ = (
        Index("ix_guest_sessions_expiry", "expires_at"),
    )

    token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
    )

    claimed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    claimed_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="guest_sessions",
    )

    conversations: Mapped[list[ConversationSession]] = relationship(
        "ConversationSession",
        back_populates="guest_session",
    )


class UserContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_contexts"

    __table_args__ = (
        Index(
            "ix_user_contexts_user_active",
            "user_id",
            "is_active",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    context_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    context_value: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    consent_given: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    consent_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="contexts",
    )



