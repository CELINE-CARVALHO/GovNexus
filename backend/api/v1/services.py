from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.core.security import get_current_admin
from backend.database.connection import get_db
from backend.database.models.administration import AdminUser
from backend.database.models.service import Service
from backend.database.models.service_version import ServiceVersion
from backend.database.models.source_fact import ServiceFactLink, SourceFact

router = APIRouter(prefix="/services", tags=["Services"])

VALID_RELATIONSHIP_TYPES = {
    "eligibility",
    "required_document",
    "application_step",
    "fee",
    "deadline",
    "general_information",
}


class ServiceFactLinkCreate(BaseModel):
    source_fact_id: UUID
    relationship_type: str = Field(default="general_information")

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                "Unsupported relationship type. "
                f"Allowed values: {sorted(VALID_RELATIONSHIP_TYPES)}"
            )
        return normalized


class ServiceVersionCreate(BaseModel):
    version_number: int | None = Field(default=None, ge=1)
    effective_from: date | None = None
    effective_to: date | None = None
    change_summary: str | None = Field(default=None, max_length=2000)


def validate_service_version_for_publication(version: ServiceVersion) -> None:
    if version.effective_from is None:
        raise ValueError("Effective start date is required for publication.")
    if version.effective_to is not None and version.effective_to < version.effective_from:
        raise ValueError("Effective-to must be on or after effective-from.")
    if not version.fact_links:
        raise ValueError("A published version must have at least one verified fact link.")
    for link in version.fact_links:
        fact = link.source_fact
        if fact.extraction_status != "verified":
            raise ValueError("Only approved facts can support publication.")


@router.get("", status_code=status.HTTP_200_OK)
def list_services(
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Service)
    if active_only:
        query = query.filter(Service.is_active.is_(True))

    rows = query.order_by(Service.code.asc()).offset(offset).limit(limit).all()
    return {
        "total": query.count(),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(item.id),
                "code": item.code,
                "slug": item.slug,
                "status": item.status,
                "is_active": item.is_active,
            }
            for item in rows
        ],
    }


@router.get("/{service_id}/versions", status_code=status.HTTP_200_OK)
def list_service_versions(
    service_id: UUID,
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    return {
        "service_id": str(service.id),
        "items": [
            {
                "id": str(version.id),
                "version_number": version.version_number,
                "effective_from": version.effective_from.isoformat()
                if version.effective_from
                else None,
                "effective_to": version.effective_to.isoformat()
                if version.effective_to
                else None,
                "publication_status": version.publication_status,
                "published_at": version.published_at.isoformat()
                if version.published_at
                else None,
            }
            for version in service.versions
        ],
    }


@router.post(
    "/{service_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
def create_service_version(
    service_id: UUID,
    payload: ServiceVersionCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version_number = payload.version_number
    if version_number is None:
        latest = (
            db.query(ServiceVersion.version_number)
            .filter(ServiceVersion.service_id == service.id)
            .order_by(ServiceVersion.version_number.desc())
            .first()
        )
        version_number = (latest[0] if latest else 0) + 1

    if payload.effective_from and payload.effective_to and payload.effective_to < payload.effective_from:
        raise HTTPException(status_code=400, detail="Effective-to must be on or after effective-from.")

    version = ServiceVersion(
        service_id=service.id,
        version_number=version_number,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        publication_status="draft",
        change_summary=payload.change_summary,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    return {
        "message": "Service version created as draft.",
        "service_id": str(service.id),
        "version": {
            "id": str(version.id),
            "version_number": version.version_number,
            "publication_status": version.publication_status,
            "effective_from": version.effective_from.isoformat() if version.effective_from else None,
            "effective_to": version.effective_to.isoformat() if version.effective_to else None,
        },
    }


@router.post(
    "/{service_id}/versions/{version_id}/publish",
    status_code=status.HTTP_200_OK,
)
def publish_service_version(
    service_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version = (
        db.query(ServiceVersion)
        .filter(ServiceVersion.id == version_id, ServiceVersion.service_id == service.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Service version not found.")

    if version.publication_status == "published":
        raise HTTPException(status_code=409, detail="This version is already published.")

    try:
        validate_service_version_for_publication(version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing_published = (
        db.query(ServiceVersion)
        .filter(
            ServiceVersion.service_id == service.id,
            ServiceVersion.publication_status == "published",
            ServiceVersion.id != version.id,
        )
        .all()
    )
    for candidate in existing_published:
        if candidate.effective_from is None:
            continue
        if candidate.effective_to is None or candidate.effective_to >= version.effective_from:
            raise HTTPException(status_code=409, detail="Conflicting active published version already exists.")

    version.publication_status = "published"
    version.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(version)

    return {
        "message": "Service version published.",
        "service_id": str(service.id),
        "version_id": str(version.id),
        "publication_status": version.publication_status,
    }


@router.get(
    "/{service_id}/versions/{version_id}/linkable-facts",
    status_code=status.HTTP_200_OK,
)
def list_linkable_facts(
    service_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version = (
        db.query(ServiceVersion)
        .filter(ServiceVersion.id == version_id, ServiceVersion.service_id == service.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Service version not found.")

    already_linked = {link.source_fact_id for link in version.fact_links}

    query = db.query(SourceFact).filter(SourceFact.extraction_status == "verified")
    if already_linked:
        query = query.filter(SourceFact.id.notin_(list(already_linked)))

    rows = query.order_by(SourceFact.created_at.desc()).all()

    return {
        "service_id": str(service.id),
        "version_id": str(version.id),
        "total": len(rows),
        "items": [
            {
                "id": str(row.id),
                "fact_type": row.fact_type,
                "fact_key": row.fact_key,
                "value_data": row.value_data,
                "evidence_locator": row.evidence_locator,
                "extraction_confidence": row.extraction_confidence,
                "extraction_status": row.extraction_status,
            }
            for row in rows
        ],
    }


@router.get(
    "/{service_id}/versions/{version_id}/facts",
    status_code=status.HTTP_200_OK,
)
def list_service_version_facts(
    service_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version = (
        db.query(ServiceVersion)
        .filter(ServiceVersion.id == version_id, ServiceVersion.service_id == service.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Service version not found.")

    rows = (
        db.query(ServiceFactLink, SourceFact)
        .join(SourceFact, SourceFact.id == ServiceFactLink.source_fact_id)
        .filter(ServiceFactLink.service_version_id == version.id)
        .order_by(SourceFact.created_at.desc())
        .all()
    )

    return {
        "service_id": str(service.id),
        "version_id": str(version.id),
        "total": len(rows),
        "items": [
            {
                "link_id": str(link.id),
                "source_fact_id": str(fact.id),
                "fact_type": fact.fact_type,
                "relationship_type": link.relationship_type,
                "value_data": fact.value_data,
                "evidence_locator": fact.evidence_locator,
                "extraction_status": fact.extraction_status,
            }
            for link, fact in rows
        ],
    }


@router.post(
    "/{service_id}/versions/{version_id}/facts",
    status_code=status.HTTP_201_CREATED,
)
def create_service_fact_link(
    service_id: UUID,
    version_id: UUID,
    payload: ServiceFactLinkCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version = (
        db.query(ServiceVersion)
        .filter(ServiceVersion.id == version_id, ServiceVersion.service_id == service.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Service version not found.")

    fact = db.query(SourceFact).filter(SourceFact.id == payload.source_fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Source fact not found.")

    if fact.extraction_status != "verified":
        raise HTTPException(
            status_code=400,
            detail="Only approved facts can be linked to a service version.",
        )

    existing = (
        db.query(ServiceFactLink)
        .filter(
            ServiceFactLink.service_version_id == version.id,
            ServiceFactLink.source_fact_id == fact.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="This fact is already linked to the selected service version.",
        )

    link = ServiceFactLink(
        service_version_id=version.id,
        source_fact_id=fact.id,
        relationship_type=payload.relationship_type,
    )

    db.add(link)
    db.commit()
    db.refresh(link)

    return {
        "message": "Service fact link created.",
        "link": {
            "id": str(link.id),
            "service_version_id": str(version.id),
            "source_fact_id": str(fact.id),
            "relationship_type": link.relationship_type,
        },
    }


@router.delete(
    "/{service_id}/versions/{version_id}/facts/{link_id}",
    status_code=status.HTTP_200_OK,
)
def remove_service_fact_link(
    service_id: UUID,
    version_id: UUID,
    link_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    version = (
        db.query(ServiceVersion)
        .filter(ServiceVersion.id == version_id, ServiceVersion.service_id == service.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Service version not found.")

    link = (
        db.query(ServiceFactLink)
        .filter(
            ServiceFactLink.id == link_id,
            ServiceFactLink.service_version_id == version.id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Service fact link not found.")

    db.delete(link)
    db.commit()

    return {
        "message": "Service fact link removed without deleting the source fact or evidence.",
        "link_id": str(link_id),
    }
