import hashlib
import hmac
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.dependencies import get_db
from backend.database.models.source import Source
from backend.services.source_ingestion import ingest_source, validate_public_url


router = APIRouter(prefix="/sources", tags=["Knowledge Sources"])


def require_source_admin(
    x_source_admin_key: str = Header(default="", alias="X-Source-Admin-Key"),
):
    configured_key = settings.SOURCE_ADMIN_API_KEY

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Source administration is not configured.",
        )

    if not hmac.compare_digest(x_source_admin_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid source administration key.",
        )


class SourceCreate(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    publisher_name: str = Field(min_length=2, max_length=255)
    source_type: str = Field(min_length=2, max_length=100)
    language_code: str | None = Field(default=None, max_length=10)
    jurisdiction_location_id: str | None = None
    retrieval_interval_hours: int = Field(default=24, ge=1, le=8760)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)

        if parsed.scheme.lower() != "https":
            raise ValueError("Only HTTPS source URLs are accepted.")

        if not parsed.hostname:
            raise ValueError("A valid hostname is required.")

        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not accepted.")

        if parsed.fragment:
            parsed = parsed._replace(fragment="")
            value = urlunsplit(parsed)

        validate_public_url(value)
        return value


class SourceUpdate(BaseModel):
    publisher_name: str | None = Field(default=None, min_length=2, max_length=255)
    source_type: str | None = Field(default=None, min_length=2, max_length=100)
    language_code: str | None = Field(default=None, max_length=10)
    jurisdiction_location_id: str | None = None
    retrieval_interval_hours: int | None = Field(default=None, ge=1, le=8760)
    is_active: bool | None = None


def source_to_dict(source: Source) -> dict:
    return {
        "id": str(source.id),
        "url": source.url,
        "publisher_name": source.publisher_name,
        "source_type": source.source_type,
        "authority_status": source.authority_status,
        "jurisdiction_location_id": (
            str(source.jurisdiction_location_id)
            if source.jurisdiction_location_id is not None
            else None
        ),
        "language_code": source.language_code,
        "retrieval_interval_hours": source.retrieval_interval_hours,
        "last_checked_at": (
            source.last_checked_at.isoformat()
            if source.last_checked_at
            else None
        ),
        "next_check_at": (
            source.next_check_at.isoformat()
            if source.next_check_at
            else None
        ),
        "content_changed_at": (
            source.content_changed_at.isoformat()
            if source.content_changed_at
            else None
        ),
        "is_active": source.is_active,
    }


def canonical_url_hash(url: str) -> str:
    parsed = urlsplit(url.strip())

    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    netloc = hostname
    if port and port != 443:
        netloc = f"{hostname}:{port}"

    canonical_url = urlunsplit((
        "https",
        netloc,
        parsed.path or "/",
        parsed.query,
        "",
    ))

    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_source_admin)],
)
def register_source(payload: SourceCreate, db: Session = Depends(get_db)):
    url_hash = canonical_url_hash(payload.url)

    existing = db.query(Source).filter(Source.url_hash == url_hash).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This source URL is already registered.",
        )

    source = Source(
        url=payload.url,
        url_hash=url_hash,
        publisher_name=payload.publisher_name.strip(),
        source_type=payload.source_type.strip(),
        authority_status="unverified",
        jurisdiction_location_id=payload.jurisdiction_location_id,
        language_code=payload.language_code,
        retrieval_interval_hours=payload.retrieval_interval_hours,
        is_active=True,
    )

    try:
        db.add(source)
        db.commit()
        db.refresh(source)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Source registered. Its authority and content remain unverified.",
        "source": source_to_dict(source),
    }


@router.get(
    "",
    dependencies=[Depends(require_source_admin)],
)
def list_sources(
    db: Session = Depends(get_db),
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(Source)

    if active_only:
        query = query.filter(Source.is_active.is_(True))

    total = query.count()

    records = (
        query.order_by(Source.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [source_to_dict(item) for item in records],
    }


@router.get(
    "/{source_id}",
    dependencies=[Depends(require_source_admin)],
)
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return source_to_dict(source)


@router.patch(
    "/{source_id}",
    dependencies=[Depends(require_source_admin)],
)
def update_source(
    source_id: str,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
):
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(source, field, value)

    try:
        db.commit()
        db.refresh(source)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Source updated.",
        "source": source_to_dict(source),
    }


@router.patch(
    "/{source_id}/activation",
    dependencies=[Depends(require_source_admin)],
)
def set_source_activation(
    source_id: str,
    is_active: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    source.is_active = is_active
    db.commit()
    db.refresh(source)

    return {
        "message": (
            "Source activated." if is_active else "Source deactivated."
        ),
        "source": source_to_dict(source),
    }


@router.post(
    "/{source_id}/ingest",
    dependencies=[Depends(require_source_admin)],
)
def trigger_source_ingest(
    source_id: str,
    db: Session = Depends(get_db),
):
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    result = ingest_source(db, source)
    db.refresh(source)

    return {
        "message": "Ingestion completed.",
        "source": source_to_dict(source),
        "ingest": result,
    }
