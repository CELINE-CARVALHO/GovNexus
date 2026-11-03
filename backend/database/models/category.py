
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint("code", name="uq_categories_code"),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )

    children: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="parent",
    )

    translations: Mapped[list[CategoryTranslation]] = relationship(
        "CategoryTranslation",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class CategoryTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "category_translations"

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "language_code",
            name="uq_category_translation_language",
        ),
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
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

    description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    category: Mapped[Category] = relationship(
        "Category",
        back_populates="translations",
    )
