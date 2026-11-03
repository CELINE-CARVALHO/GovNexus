from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from backend.database.connection import get_db
from backend.database.models.language import Language
from backend.database.models.department import Department, DepartmentTranslation
from backend.database.models.category import Category, CategoryTranslation
from backend.database.models.location import Location, LocationTranslation
from backend.database.models.service import Service
from backend.database.models.service_version import ServiceVersion, ServiceTranslation

router = APIRouter(tags=["Government Catalogue"])


def paginate(items: list[dict[str, Any]], total: int, page: int, limit: int):
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/languages")
def list_languages(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Language)

    if active_only:
        query = query.filter(Language.is_active.is_(True))

    rows = query.order_by(Language.english_name).all()

    return {
        "items": [
            {
                "code": row.code,
                "english_name": row.english_name,
                "native_name": row.native_name,
                "is_active": row.is_active,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/departments")
def list_departments(
    language: str = Query("en", min_length=2, max_length=10),
    search: str | None = Query(None, max_length=150),
    parent_id: UUID | None = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    requested = aliased(DepartmentTranslation)
    english = aliased(DepartmentTranslation)

    query = (
        db.query(
            Department,
            func.coalesce(requested.name, english.name).label("name"),
            func.coalesce(
                requested.description, english.description
            ).label("description"),
        )
        .outerjoin(
            requested,
            (requested.department_id == Department.id)
            & (requested.language_code == language),
        )
        .outerjoin(
            english,
            (english.department_id == Department.id)
            & (english.language_code == "en"),
        )
    )

    if active_only:
        query = query.filter(Department.is_active.is_(True))

    if parent_id is not None:
        query = query.filter(Department.parent_id == parent_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Department.code.ilike(term),
                requested.name.ilike(term),
                english.name.ilike(term),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Department.code)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": str(item.id),
            "code": item.code,
            "name": name,
            "description": description,
            "level": item.level,
            "parent_id": str(item.parent_id) if item.parent_id else None,
            "website_url": item.website_url,
            "is_active": item.is_active,
        }
        for item, name, description in rows
    ]

    return paginate(items, total, page, limit)


@router.get("/categories")
def list_categories(
    language: str = Query("en", min_length=2, max_length=10),
    search: str | None = Query(None, max_length=150),
    parent_id: UUID | None = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    requested = aliased(CategoryTranslation)
    english = aliased(CategoryTranslation)

    query = (
        db.query(
            Category,
            func.coalesce(requested.name, english.name).label("name"),
            func.coalesce(
                requested.description, english.description
            ).label("description"),
        )
        .outerjoin(
            requested,
            (requested.category_id == Category.id)
            & (requested.language_code == language),
        )
        .outerjoin(
            english,
            (english.category_id == Category.id)
            & (english.language_code == "en"),
        )
    )

    if active_only:
        query = query.filter(Category.is_active.is_(True))

    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Category.code.ilike(term),
                requested.name.ilike(term),
                english.name.ilike(term),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Category.code)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": str(item.id),
            "code": item.code,
            "name": name,
            "description": description,
            "parent_id": str(item.parent_id) if item.parent_id else None,
            "is_active": item.is_active,
        }
        for item, name, description in rows
    ]

    return paginate(items, total, page, limit)


@router.get("/locations")
def list_locations(
    language: str = Query("en", min_length=2, max_length=10),
    search: str | None = Query(None, max_length=150),
    location_type: str | None = Query(None, max_length=30),
    parent_id: UUID | None = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    requested = aliased(LocationTranslation)
    english = aliased(LocationTranslation)

    query = (
        db.query(
            Location,
            func.coalesce(requested.name, english.name).label("name"),
        )
        .outerjoin(
            requested,
            (requested.location_id == Location.id)
            & (requested.language_code == language),
        )
        .outerjoin(
            english,
            (english.location_id == Location.id)
            & (english.language_code == "en"),
        )
    )

    if active_only:
        query = query.filter(Location.is_active.is_(True))

    if location_type:
        query = query.filter(Location.location_type == location_type)

    if parent_id is not None:
        query = query.filter(Location.parent_id == parent_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Location.code.ilike(term),
                requested.name.ilike(term),
                english.name.ilike(term),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Location.location_type, Location.code)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": str(item.id),
            "name": name,
            "code": item.code,
            "location_type": item.location_type,
            "parent_id": str(item.parent_id) if item.parent_id else None,
            "is_active": item.is_active,
        }
        for item, name in rows
    ]

    return paginate(items, total, page, limit)


def published_service_query(db: Session, language: str):
    requested = aliased(ServiceTranslation)
    english = aliased(ServiceTranslation)

    latest_version = (
        db.query(func.max(ServiceVersion.version_number))
        .filter(
            ServiceVersion.service_id == Service.id,
            ServiceVersion.publication_status == "published",
        )
        .correlate(Service)
        .scalar_subquery()
    )

    return (
        db.query(
            Service,
            ServiceVersion,
            func.coalesce(requested.title, english.title).label("title"),
            func.coalesce(
                requested.description, english.description
            ).label("description"),
            func.coalesce(
                requested.application_url, english.application_url
            ).label("application_url"),
        )
        .join(
            ServiceVersion,
            (ServiceVersion.service_id == Service.id)
            & (ServiceVersion.version_number == latest_version)
            & (ServiceVersion.publication_status == "published"),
        )
        .outerjoin(
            requested,
            (requested.service_version_id == ServiceVersion.id)
            & (requested.language_code == language),
        )
        .outerjoin(
            english,
            (english.service_version_id == ServiceVersion.id)
            & (english.language_code == "en"),
        )
    )


@router.get("/services")
def list_services(
    language: str = Query("en", min_length=2, max_length=10),
    search: str | None = Query(None, max_length=150),
    department_id: UUID | None = None,
    category_id: UUID | None = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = published_service_query(db, language)

    if active_only:
        query = query.filter(
            Service.is_active.is_(True),
            Service.status == "active",
        )

    if department_id:
        query = query.filter(Service.department_id == department_id)

    if category_id:
        query = query.filter(Service.category_id == category_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Service.code.ilike(term),
                Service.slug.ilike(term),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Service.code)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": str(service.id),
            "code": service.code,
            "slug": service.slug,
            "title": title,
            "description": description,
            "application_url": application_url,
            "department_id": str(service.department_id),
            "category_id": str(service.category_id),
            "version_id": str(version.id),
            "version_number": version.version_number,
            "effective_from": (
                version.effective_from.isoformat()
                if version.effective_from else None
            ),
        }
        for service, version, title, description, application_url in rows
    ]

    return paginate(items, total, page, limit)


@router.get("/services/{service_id}")
def get_service(
    service_id: UUID,
    language: str = Query("en", min_length=2, max_length=10),
    db: Session = Depends(get_db),
):
    row = (
        published_service_query(db, language)
        .filter(
            Service.id == service_id,
            Service.is_active.is_(True),
        )
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Published service not found",
        )

    service, version, title, description, application_url = row

    return {
        "id": str(service.id),
        "code": service.code,
        "slug": service.slug,
        "status": service.status,
        "title": title,
        "description": description,
        "application_url": application_url,
        "department_id": str(service.department_id),
        "category_id": str(service.category_id),
        "version": {
            "id": str(version.id),
            "number": version.version_number,
            "effective_from": (
                version.effective_from.isoformat()
                if version.effective_from else None
            ),
            "effective_to": (
                version.effective_to.isoformat()
                if version.effective_to else None
            ),
            "change_summary": version.change_summary,
        },
    }

# ============================================================
# DETAILED SERVICE INFORMATION
# ============================================================

from backend.database.models.service_details import (
    ServiceJurisdiction,
    EligibilityRule,
    EligibilityTranslation,
    RequiredDocument,
    DocumentTranslation,
    ApplicationStep,
    StepTranslation,
)

from backend.database.models.location import (
    Location,
    LocationTranslation,
)

from backend.database.models.source_fact import (
    ServiceFactLink,
    SourceFact,
    SourceSnapshot,
)

from backend.database.models.source import Source
from backend.database.models.verification import FactVerification


def translated_value(rows, language, field, fallback_field=None):
    """
    Return requested-language content, falling back to English.
    Never invent a translation when neither exists.
    """
    requested = next(
        (row for row in rows if row.language_code == language),
        None,
    )

    english = next(
        (row for row in rows if row.language_code == "en"),
        None,
    )

    selected = requested or english

    if selected is None:
        return None

    result = getattr(selected, field)

    if fallback_field:
        return {
            field: result,
            fallback_field: getattr(selected, fallback_field),
        }

    return result


@router.get("/services/{service_id}/details")
def get_service_details(
    service_id: UUID,
    language: str = Query("en", min_length=2, max_length=10),
    db: Session = Depends(get_db),
):
    """
    Return the complete published service information.

    Only published service versions are exposed.
    Source verification is returned separately from extracted facts.
    """

    # --------------------------------------------------------
    # 1. Find the currently published service version
    # --------------------------------------------------------

    row = (
        published_service_query(db, language)
        .filter(
            Service.id == service_id,
            Service.is_active.is_(True),
            Service.status == "active",
        )
        .first()
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Published service not found",
        )

    service, version, title, description, application_url = row
    version_id = version.id

    # --------------------------------------------------------
    # 2. Eligibility criteria
    # --------------------------------------------------------

    eligibility_rules = (
        db.query(EligibilityRule)
        .filter(
            EligibilityRule.service_version_id == version_id
        )
        .order_by(
            EligibilityRule.display_order,
            EligibilityRule.created_at,
        )
        .all()
    )

    eligibility_ids = [item.id for item in eligibility_rules]

    eligibility_translations = []

    if eligibility_ids:
        eligibility_translations = (
            db.query(EligibilityTranslation)
            .filter(
                EligibilityTranslation.eligibility_rule_id.in_(
                    eligibility_ids
                ),
                EligibilityTranslation.language_code.in_(
                    [language, "en"]
                ),
            )
            .all()
        )

    eligibility = []

    for rule in eligibility_rules:
        translations = [
            item
            for item in eligibility_translations
            if item.eligibility_rule_id == rule.id
        ]

        eligibility.append({
            "id": str(rule.id),
            "rule_type": rule.rule_type,
            "operator": rule.operator,
            "condition": rule.condition_data,
            "description": translated_value(
                translations,
                language,
                "description",
            ),
            "is_mandatory": rule.is_mandatory,
            "display_order": rule.display_order,
            "translation_available": any(
                item.language_code == language
                for item in translations
            ),
        })

    # --------------------------------------------------------
    # 3. Required documents
    # --------------------------------------------------------

    required_documents = (
        db.query(RequiredDocument)
        .filter(
            RequiredDocument.service_version_id == version_id
        )
        .order_by(
            RequiredDocument.display_order,
            RequiredDocument.created_at,
        )
        .all()
    )

    document_ids = [item.id for item in required_documents]

    document_translations = []

    if document_ids:
        document_translations = (
            db.query(DocumentTranslation)
            .filter(
                DocumentTranslation.required_document_id.in_(
                    document_ids
                ),
                DocumentTranslation.language_code.in_(
                    [language, "en"]
                ),
            )
            .all()
        )

    documents = []

    for document in required_documents:
        translations = [
            item
            for item in document_translations
            if item.required_document_id == document.id
        ]

        selected = next(
            (
                item for item in translations
                if item.language_code == language
            ),
            None,
        ) or next(
            (
                item for item in translations
                if item.language_code == "en"
            ),
            None,
        )

        documents.append({
            "id": str(document.id),
            "document_code": document.document_code,
            "name": selected.name if selected else None,
            "description": (
                selected.description if selected else None
            ),
            "is_mandatory": document.is_mandatory,
            "copies_required": document.copies_required,
            "accepted_formats": document.accepted_formats,
            "conditional_rule": document.conditional_rule,
            "display_order": document.display_order,
            "translation_available": any(
                item.language_code == language
                for item in translations
            ),
        })

    # --------------------------------------------------------
    # 4. Application steps
    # --------------------------------------------------------

    application_steps = (
        db.query(ApplicationStep)
        .filter(
            ApplicationStep.service_version_id == version_id
        )
        .order_by(ApplicationStep.step_number)
        .all()
    )

    step_ids = [item.id for item in application_steps]

    step_translations = []

    if step_ids:
        step_translations = (
            db.query(StepTranslation)
            .filter(
                StepTranslation.application_step_id.in_(step_ids),
                StepTranslation.language_code.in_(
                    [language, "en"]
                ),
            )
            .all()
        )

    steps = []

    for step in application_steps:
        translations = [
            item
            for item in step_translations
            if item.application_step_id == step.id
        ]

        selected = next(
            (
                item for item in translations
                if item.language_code == language
            ),
            None,
        ) or next(
            (
                item for item in translations
                if item.language_code == "en"
            ),
            None,
        )

        steps.append({
            "id": str(step.id),
            "step_number": step.step_number,
            "step_type": step.step_type,
            "title": selected.title if selected else None,
            "instructions": (
                selected.instructions if selected else None
            ),
            "official_url": step.official_url,
            "is_optional": step.is_optional,
            "translation_available": any(
                item.language_code == language
                for item in translations
            ),
        })

    # --------------------------------------------------------
    # 5. Applicable jurisdictions
    # --------------------------------------------------------

    jurisdictions = (
        db.query(ServiceJurisdiction)
        .filter(
            ServiceJurisdiction.service_version_id == version_id
        )
        .all()
    )

    location_ids = [
        item.location_id for item in jurisdictions
    ]

    locations = {}

    if location_ids:
        location_rows = (
            db.query(Location)
            .filter(Location.id.in_(location_ids))
            .all()
        )

        location_translations = (
            db.query(LocationTranslation)
            .filter(
                LocationTranslation.location_id.in_(location_ids),
                LocationTranslation.language_code.in_(
                    [language, "en"]
                ),
            )
            .all()
        )

        for location in location_rows:
            translations = [
                item
                for item in location_translations
                if item.location_id == location.id
            ]

            selected = next(
                (
                    item for item in translations
                    if item.language_code == language
                ),
                None,
            ) or next(
                (
                    item for item in translations
                    if item.language_code == "en"
                ),
                None,
            )

            locations[location.id] = {
                "id": str(location.id),
                "name": selected.name if selected else None,
                "location_type": location.location_type,
                "code": location.code,
                "translation_available": any(
                    item.language_code == language
                    for item in translations
                ),
            }

    jurisdiction_data = []

    for item in jurisdictions:
        jurisdiction_data.append({
            "location": locations.get(item.location_id),
            "coverage_type": item.coverage_type,
            "notes": item.notes,
        })

    # --------------------------------------------------------
    # 6. Linked source evidence and verification
    # --------------------------------------------------------

    linked_facts = (
        db.query(
            ServiceFactLink,
            SourceFact,
            SourceSnapshot,
            Source,
        )
        .join(
            SourceFact,
            ServiceFactLink.source_fact_id == SourceFact.id,
        )
        .join(
            SourceSnapshot,
            SourceFact.source_snapshot_id == SourceSnapshot.id,
        )
        .join(
            Source,
            SourceSnapshot.source_id == Source.id,
        )
        .filter(
            ServiceFactLink.service_version_id == version_id
        )
        .all()
    )

    evidence = []

    for link, fact, snapshot, source in linked_facts:

        verification = (
            db.query(FactVerification)
            .filter(
                FactVerification.source_fact_id == fact.id
            )
            .order_by(
                FactVerification.verified_at.desc()
            )
            .first()
        )

        verification_status = (
            verification.verification_status
            if verification else "not_reviewed"
        )

        verification_decision = (
            verification.decision
            if verification else None
        )

        is_verified = (
            str(verification_status).lower() == "verified"
            and str(verification_decision).lower()
            in {"approved", "approve", "accepted", "accept"}
        )

        evidence.append({
            "fact_id": str(fact.id),
            "fact_key": fact.fact_key,
            "fact_type": fact.fact_type,
            "value": fact.value_data,
            "evidence_locator": fact.evidence_locator,
            "extraction_status": fact.extraction_status,
            "extraction_confidence": fact.extraction_confidence,
            "relationship_type": link.relationship_type,
            "source": {
                "publisher": source.publisher_name,
                "url": source.url,
                "source_type": source.source_type,
                "authority_status": source.authority_status,
                "is_active": source.is_active,
            },
            "snapshot": {
                "fetched_at": snapshot.fetched_at.isoformat(),
                "content_hash": snapshot.content_hash,
                "extraction_status": snapshot.extraction_status,
            },
            "verification": {
                "status": verification_status,
                "decision": verification_decision,
                "verified_at": (
                    verification.verified_at.isoformat()
                    if verification else None
                ),
                "notes": verification.notes if verification else None,
                "is_verified": is_verified,
            },
        })

    # --------------------------------------------------------
    # 7. Complete response
    # --------------------------------------------------------

    return {
        "service": {
            "id": str(service.id),
            "code": service.code,
            "slug": service.slug,
            "status": service.status,
            "title": title,
            "description": description,
            "application_url": application_url,
            "department_id": str(service.department_id),
            "category_id": str(service.category_id),
        },

        "version": {
            "id": str(version.id),
            "number": version.version_number,
            "publication_status": version.publication_status,
            "published_at": (
                version.published_at.isoformat()
                if version.published_at else None
            ),
            "effective_from": (
                version.effective_from.isoformat()
                if version.effective_from else None
            ),
            "effective_to": (
                version.effective_to.isoformat()
                if version.effective_to else None
            ),
            "change_summary": version.change_summary,
        },

        "language": {
            "requested": language,
            "fallback": "en",
        },

        "eligibility": eligibility,
        "required_documents": documents,
        "application_steps": steps,
        "jurisdictions": jurisdiction_data,

        "evidence": {
            "items": evidence,
            "total": len(evidence),
            "verified_count": sum(
                1 for item in evidence
                if item["verification"]["is_verified"]
            ),
            "unverified_count": sum(
                1 for item in evidence
                if not item["verification"]["is_verified"]
            ),
        },

        "disclaimer": (
            "Eligibility and application information is provided "
            "from the published service record. Check the linked "
            "official sources for the latest requirements. "
            "Evidence without an approved verification record "
            "must not be treated as verified."
        ),
    }

