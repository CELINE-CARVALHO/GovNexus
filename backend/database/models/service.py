
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.database.models.common import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Service(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "services"

    __table_args__ = (
        Index("ix_services_department", "department_id"),
        Index("ix_services_category", "category_id"),
        Index("ix_services_status", "status"),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )

    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id"),
        nullable=False,
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    department: Mapped[Department] = relationship(
        "Department",
    )

    category: Mapped[Category] = relationship(
        "Category",
    )

    versions: Mapped[list[ServiceVersion]] = relationship(
        "ServiceVersion",
        back_populates="service",
        cascade="all, delete-orphan",
        order_by="ServiceVersion.version_number",
    )
