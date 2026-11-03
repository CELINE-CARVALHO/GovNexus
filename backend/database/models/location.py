
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"

    __table_args__ = (
        UniqueConstraint(
            "parent_id",
            "code",
            name="uq_locations_parent_code",
        ),
        Index("ix_locations_type", "location_type"),
    )

    location_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    parent: Mapped[Location | None] = relationship(
        "Location",
        remote_side="Location.id",
        back_populates="children",
    )

    children: Mapped[list[Location]] = relationship(
        "Location",
        back_populates="parent",
    )

    translations: Mapped[list[LocationTranslation]] = relationship(
        "LocationTranslation",
        back_populates="location",
        cascade="all, delete-orphan",
    )


class LocationTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "location_translations"

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "language_code",
            name="uq_location_translation_language",
        ),
    )

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    location: Mapped[Location] = relationship(
        "Location",
        back_populates="translations",
    )
