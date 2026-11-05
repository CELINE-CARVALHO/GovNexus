from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.security import get_current_admin
from backend.database.connection import get_db
from backend.database.models.administration import AdminUser
from backend.database.models.category import Category, CategoryTranslation
from backend.database.models.citizen import User
from backend.database.models.department import Department, DepartmentTranslation
from backend.database.models.language import Language
from backend.database.models.operations import IngestionJob
from backend.database.models.service import Service
from backend.database.models.service_version import ServiceVersion
from backend.database.models.source import Source
from backend.database.models.source_fact import SourceFact
from backend.database.models.verification import (
    FactDuplicateCandidate,
    ReviewTask,
)


router = APIRouter(prefix="/admin", tags=["Administration"])

class TranslationInput(BaseModel):
    language_code: str = Field(min_length=2, max_length=10)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("language_code")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Translation name is required.")
        return value


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    level: str = Field(min_length=2, max_length=30)
    parent_id: UUID | None = None
    website_url: AnyHttpUrl | None = None
    translations: list[TranslationInput] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_translation_languages(self):
        codes = [item.language_code for item in self.translations]
        if len(codes) != len(set(codes)):
            raise ValueError("Translation language codes must be unique.")
        return self

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class DepartmentUpdate(BaseModel):
    level: str | None = Field(default=None, min_length=2, max_length=30)
    parent_id: UUID | None = None
    website_url: AnyHttpUrl | None = None
    is_active: bool | None = None
    translations: list[TranslationInput] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def unique_translation_languages(self):
        if self.translations is not None:
            codes = [item.language_code for item in self.translations]
            if len(codes) != len(set(codes)):
                raise ValueError("Translation language codes must be unique.")
        return self


class CategoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    parent_id: UUID | None = None
    translations: list[TranslationInput] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_translation_languages(self):
        codes = [item.language_code for item in self.translations]
        if len(codes) != len(set(codes)):
            raise ValueError("Translation language codes must be unique.")
        return self

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CategoryUpdate(BaseModel):
    parent_id: UUID | None = None
    is_active: bool | None = None
    translations: list[TranslationInput] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def unique_translation_languages(self):
        if self.translations is not None:
            codes = [item.language_code for item in self.translations]
            if len(codes) != len(set(codes)):
                raise ValueError("Translation language codes must be unique.")
        return self


def _count(db: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


@router.get("/dashboard")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    current_date = func.current_date()
    current_published_service_ids = (
        select(func.distinct(ServiceVersion.service_id))
        .join(Service, Service.id == ServiceVersion.service_id)
        .where(
            Service.is_active.is_(True),
            Service.status == "active",
            ServiceVersion.publication_status == "published",
            (ServiceVersion.effective_from.is_(None))
            | (ServiceVersion.effective_from <= current_date),
            (ServiceVersion.effective_to.is_(None))
            | (ServiceVersion.effective_to >= current_date),
        )
    )
    return {
        "sources": {
            "total": _count(db, Source),
            "active": _count(db, Source, Source.is_active.is_(True)),
        },
        "facts": {
            "total": _count(db, SourceFact),
            "verified": _count(
                db,
                SourceFact,
                SourceFact.extraction_status == "verified",
            ),
            "pending_review": _count(
                db,
                SourceFact,
                SourceFact.extraction_status.in_(("pending", "pending_review")),
            ),
            "rejected": _count(
                db,
                SourceFact,
                SourceFact.extraction_status == "rejected",
            ),
        },
        "services": {
            "total": _count(db, Service),
            "active": _count(db, Service, Service.is_active.is_(True)),
            "currently_published": int(
                db.scalar(
                    select(func.count()).select_from(
                        current_published_service_ids.subquery()
                    )
                )
                or 0
            ),
        },
        "review": {
            "open_tasks": _count(
                db,
                ReviewTask,
                ReviewTask.status.in_(("open", "pending")),
            ),
            "pending_duplicate_suggestions": _count(
                db,
                FactDuplicateCandidate,
                FactDuplicateCandidate.review_status == "pending",
            ),
        },
        "ingestion": {
            "total_jobs": _count(db, IngestionJob),
            "pending": _count(db, IngestionJob, IngestionJob.status == "pending"),
            "running": _count(db, IngestionJob, IngestionJob.status == "running"),
            "failed": _count(db, IngestionJob, IngestionJob.status == "failed"),
        },
        "citizens": {
            "total": _count(db, User),
            "active": _count(db, User, User.account_status == "active"),
        },
    }


@router.get("/services")
def list_admin_services(
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    query = select(Service)
    if active_only:
        query = query.where(Service.is_active.is_(True))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Service.code.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "total": total,
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


def _validate_parent(
    db: Session,
    model,
    parent_id: UUID | None,
    entity_id: UUID | None = None,
) -> None:
    if parent_id is None:
        return
    if entity_id is not None and parent_id == entity_id:
        raise HTTPException(status_code=422, detail="An item cannot be its own parent.")
    parent = db.get(model, parent_id)
    if parent is None:
        raise HTTPException(status_code=422, detail="Selected parent does not exist.")
    visited = set()
    while parent is not None:
        if parent.id == entity_id or parent.id in visited:
            raise HTTPException(status_code=422, detail="Parent selection would create a hierarchy cycle.")
        visited.add(parent.id)
        parent = db.get(model, parent.parent_id) if parent.parent_id else None


def _sync_translations(
    db: Session,
    *,
    model,
    foreign_key: str,
    entity_id: UUID,
    translations: list[TranslationInput],
) -> None:
    language_codes = {item.language_code for item in translations}
    active_languages = set(
        db.scalars(
            select(Language.code).where(
                Language.code.in_(language_codes),
                Language.is_active.is_(True),
            )
        ).all()
    )
    if active_languages != language_codes:
        raise HTTPException(
            status_code=422,
            detail="Every translation must use an active language.",
        )
    for translation in translations:
        record = db.scalar(
            select(model).where(
                getattr(model, foreign_key) == entity_id,
                model.language_code == translation.language_code,
            )
        )
        if record is None:
            record = model(
                **{
                    foreign_key: entity_id,
                    "language_code": translation.language_code,
                }
            )
            db.add(record)
        record.name = translation.name
        record.description = translation.description


def _department_result(item: Department) -> dict:
    return {
        "id": str(item.id),
        "code": item.code,
        "level": item.level,
        "parent_id": str(item.parent_id) if item.parent_id else None,
        "website_url": item.website_url,
        "is_active": item.is_active,
    }


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    _validate_parent(db, Department, payload.parent_id)
    department = Department(
        code=payload.code,
        level=payload.level.strip().lower(),
        parent_id=payload.parent_id,
        website_url=str(payload.website_url) if payload.website_url else None,
        is_active=True,
    )
    db.add(department)
    try:
        db.flush()
        _sync_translations(
            db,
            model=DepartmentTranslation,
            foreign_key="department_id",
            entity_id=department.id,
            translations=payload.translations,
        )
        db.commit()
        db.refresh(department)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this code already exists.") from exc
    return _department_result(department)


@router.patch("/departments/{department_id}")
def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        _validate_parent(db, Department, changes["parent_id"], department.id)
        department.parent_id = changes["parent_id"]
    if "level" in changes and changes["level"] is not None:
        department.level = changes["level"].strip().lower()
    if "website_url" in changes:
        value = changes["website_url"]
        department.website_url = str(value) if value else None
    if "is_active" in changes and changes["is_active"] is not None:
        department.is_active = changes["is_active"]
    if changes.get("translations") is not None:
        _sync_translations(
            db,
            model=DepartmentTranslation,
            foreign_key="department_id",
            entity_id=department.id,
            translations=changes["translations"],
        )
    try:
        db.commit()
        db.refresh(department)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Department update conflicts with existing data.") from exc
    return _department_result(department)


def _category_result(item: Category) -> dict:
    return {
        "id": str(item.id),
        "code": item.code,
        "parent_id": str(item.parent_id) if item.parent_id else None,
        "is_active": item.is_active,
    }


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    _validate_parent(db, Category, payload.parent_id)
    category = Category(
        code=payload.code,
        parent_id=payload.parent_id,
        is_active=True,
    )
    db.add(category)
    try:
        db.flush()
        _sync_translations(
            db,
            model=CategoryTranslation,
            foreign_key="category_id",
            entity_id=category.id,
            translations=payload.translations,
        )
        db.commit()
        db.refresh(category)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A category with this code already exists.") from exc
    return _category_result(category)


@router.patch("/categories/{category_id}")
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        _validate_parent(db, Category, changes["parent_id"], category.id)
        category.parent_id = changes["parent_id"]
    if "is_active" in changes and changes["is_active"] is not None:
        category.is_active = changes["is_active"]
    if changes.get("translations") is not None:
        _sync_translations(
            db,
            model=CategoryTranslation,
            foreign_key="category_id",
            entity_id=category.id,
            translations=changes["translations"],
        )
    try:
        db.commit()
        db.refresh(category)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category update conflicts with existing data.") from exc
    return _category_result(category)