
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


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    __table_args__ = (
        UniqueConstraint("code", name="uq_departments_code"),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )

    website_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
    )

    children: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="parent",
    )

    translations: Mapped[list[DepartmentTranslation]] = relationship(
        "DepartmentTranslation",
        back_populates="department",
        cascade="all, delete-orphan",
    )


class DepartmentTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "department_translations"

    __table_args__ = (
        UniqueConstraint(
            "department_id",
            "language_code",
            name="uq_department_translation_language",
        ),
    )

    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
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

    department: Mapped[Department] = relationship(
        "Department",
        back_populates="translations",
    )
