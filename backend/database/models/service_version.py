from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
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


class ServiceVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_versions"

    __table_args__ = (
        UniqueConstraint(
            "service_id",
            "version_number",
            name="uq_service_version_number",
        ),
    )

    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    effective_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    publication_status: Mapped[str] = mapped_column(
        String(30),
        default="draft",
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(),
        nullable=True,
    )

    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    service: Mapped[Service] = relationship(
        "Service",
        back_populates="versions",
    )

    translations: Mapped[list[ServiceTranslation]] = relationship(
        "ServiceTranslation",
        back_populates="service_version",
        cascade="all, delete-orphan",
    )

    jurisdictions: Mapped[list[ServiceJurisdiction]] = relationship(
        "ServiceJurisdiction",
        back_populates="service_version",
        cascade="all, delete-orphan",
    )

    eligibility_rules: Mapped[list[EligibilityRule]] = relationship(
        "EligibilityRule",
        back_populates="service_version",
        cascade="all, delete-orphan",
    )

    required_documents: Mapped[list[RequiredDocument]] = relationship(
        "RequiredDocument",
        back_populates="service_version",
        cascade="all, delete-orphan",
    )

    application_steps: Mapped[list[ApplicationStep]] = relationship(
        "ApplicationStep",
        back_populates="service_version",
        cascade="all, delete-orphan",
        order_by="ApplicationStep.step_number",
    )

    fact_links: Mapped[list[ServiceFactLink]] = relationship(
        "ServiceFactLink",
        back_populates="service_version",
    )

    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="service_version",
    )


class ServiceTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "service_translations"

    __table_args__ = (
        UniqueConstraint(
            "service_version_id",
            "language_code",
            name="uq_service_translation_language",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    application_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="translations",
    )
