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


class ServiceJurisdiction(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "service_jurisdictions"

    __table_args__ = (
        UniqueConstraint(
            "service_version_id",
            "location_id",
            name="uq_service_jurisdiction_location",
        ),
        Index(
            "ix_service_jurisdictions_location",
            "location_id",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    coverage_type: Mapped[str] = mapped_column(
        String(30),
        default="available",
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="jurisdictions",
    )

    location: Mapped[Location] = relationship("Location")


class EligibilityRule(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "eligibility_rules"

    __table_args__ = (
        Index(
            "ix_eligibility_rules_service_version",
            "service_version_id",
        ),
        Index(
            "ix_eligibility_rules_type",
            "rule_type",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    rule_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    operator: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="equals",
    )

    # Example: {"value": 18, "unit": "years"}
    # Store structured conditions, not executable expressions.
    condition_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="eligibility_rules",
    )

    translations: Mapped[list[EligibilityTranslation]] = relationship(
        "EligibilityTranslation",
        back_populates="eligibility_rule",
        cascade="all, delete-orphan",
    )


class EligibilityTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "eligibility_translations"

    __table_args__ = (
        UniqueConstraint(
            "eligibility_rule_id",
            "language_code",
            name="uq_eligibility_translation_language",
        ),
    )

    eligibility_rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("eligibility_rules.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    eligibility_rule: Mapped[EligibilityRule] = relationship(
        "EligibilityRule",
        back_populates="translations",
    )


class RequiredDocument(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "required_documents"

    __table_args__ = (
        Index(
            "ix_required_documents_service_version",
            "service_version_id",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    document_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    copies_required: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    accepted_formats: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    conditional_rule: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="required_documents",
    )

    translations: Mapped[list[DocumentTranslation]] = relationship(
        "DocumentTranslation",
        back_populates="required_document",
        cascade="all, delete-orphan",
    )


class DocumentTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "document_translations"

    __table_args__ = (
        UniqueConstraint(
            "required_document_id",
            "language_code",
            name="uq_document_translation_language",
        ),
    )

    required_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("required_documents.id", ondelete="CASCADE"),
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
        Text,
        nullable=True,
    )

    required_document: Mapped[RequiredDocument] = relationship(
        "RequiredDocument",
        back_populates="translations",
    )


class ApplicationStep(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "application_steps"

    __table_args__ = (
        UniqueConstraint(
            "service_version_id",
            "step_number",
            name="uq_application_step_number",
        ),
        Index(
            "ix_application_steps_service_version",
            "service_version_id",
        ),
    )

    service_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    step_type: Mapped[str] = mapped_column(
        String(40),
        default="general",
        nullable=False,
    )

    official_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    is_optional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    service_version: Mapped[ServiceVersion] = relationship(
        "ServiceVersion",
        back_populates="application_steps",
    )

    translations: Mapped[list[StepTranslation]] = relationship(
        "StepTranslation",
        back_populates="application_step",
        cascade="all, delete-orphan",
    )


class StepTranslation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "step_translations"

    __table_args__ = (
        UniqueConstraint(
            "application_step_id",
            "language_code",
            name="uq_step_translation_language",
        ),
    )

    application_step_id: Mapped[UUID] = mapped_column(
        ForeignKey("application_steps.id", ondelete="CASCADE"),
        nullable=False,
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("languages.code"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    application_step: Mapped[ApplicationStep] = relationship(
        "ApplicationStep",
        back_populates="translations",
    )
