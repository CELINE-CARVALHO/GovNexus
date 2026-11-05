from datetime import date, datetime, time, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.security import get_current_citizen
from backend.database.connection import get_db
from backend.database.models.applications import (
    ApplicationStatusHistory,
    CitizenApplication,
)
from backend.database.models.citizen import User, UserProfile
from backend.database.models.conversation import (
    ConversationMessage,
    ConversationSession,
    SavedService,
)
from backend.database.models.language import Language
from backend.database.models.location import Location
from backend.database.models.service import Service
from backend.database.models.service_details import RequiredDocument
from backend.api.v1.catalogue import published_service_query


router = APIRouter(prefix="/users", tags=["Citizen Account"])

APPLICATION_STATUSES = {
    "planning",
    "submitted_externally",
    "under_review",
    "additional_information_requested",
    "approved",
    "rejected",
    "withdrawn",
    "completed",
}
NOTIFICATION_KEYS = {"email", "sms", "in_app"}
DEFAULT_ACCESSIBILITY_PREFERENCES = {
    "font_size": "medium",
    "text_scale_percent": 100,
    "high_contrast": False,
    "increased_spacing": False,
    "large_buttons": False,
    "simple_mode": False,
    "read_aloud": False,
    "reduced_motion": False,
}


class AccessibilityPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font_size: Literal["small", "medium", "large", "extra_large"] = "medium"
    text_scale_percent: int = Field(default=100, ge=80, le=200)
    high_contrast: bool = False
    increased_spacing: bool = False
    large_buttons: bool = False
    simple_mode: bool = False
    read_aloud: bool = False
    reduced_motion: bool = False


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    preferred_language_code: str | None = Field(default=None, min_length=2, max_length=10)
    state_id: UUID | None = None
    district_id: UUID | None = None
    date_of_birth: date | None = None
    notification_preferences: dict[str, bool] | None = None
    accessibility_preferences: AccessibilityPreferences | None = None

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be empty.")
        return value

    @field_validator("preferred_language_code")
    @classmethod
    def normalize_language(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    language_code: str | None = Field(default=None, min_length=2, max_length=10)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Conversation title cannot be empty.")
        return value


class ChecklistItemUpdate(BaseModel):
    document_id: UUID
    completed: bool


class ApplicationCreate(BaseModel):
    service_id: UUID
    reference_number: str | None = Field(default=None, max_length=255)
    application_date: date | None = None
    status: str = "planning"
    notes: str | None = Field(default=None, max_length=5000)
    document_checklist: list[ChecklistItemUpdate] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in APPLICATION_STATUSES:
            raise ValueError("Unsupported citizen-recorded application status.")
        return normalized


class ApplicationUpdate(BaseModel):
    reference_number: str | None = Field(default=None, max_length=255)
    application_date: date | None = None
    status: str | None = None
    notes: str | None = Field(default=None, max_length=5000)
    document_checklist: list[ChecklistItemUpdate] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in APPLICATION_STATUSES:
            raise ValueError("Unsupported citizen-recorded application status.")
        return normalized


def _ensure_profile(user: User) -> UserProfile:
    if user.profile is None:
        user.profile = UserProfile()
    return user.profile


def _profile_response(user: User) -> dict[str, Any]:
    profile = user.profile
    metadata = profile.profile_metadata if profile and profile.profile_metadata else {}
    return {
        "id": str(user.id),
        "email": user.email,
        "phone_number": user.phone_number,
        "preferred_language_code": user.preferred_language_code,
        "display_name": profile.display_name if profile else None,
        "date_of_birth": (
            profile.date_of_birth.date().isoformat()
            if profile and profile.date_of_birth
            else None
        ),
        "state_id": metadata.get("state_id"),
        "district_id": metadata.get("district_id"),
        "notification_preferences": metadata.get("notification_preferences", {}),
        "accessibility_preferences": {
            **DEFAULT_ACCESSIBILITY_PREFERENCES,
            **(metadata.get("accessibility_preferences") or {}),
        },
        "account_status": user.account_status,
    }


@router.get("/me")
def get_my_profile(
    current_citizen: User = Depends(get_current_citizen),
):
    return _profile_response(current_citizen)


@router.patch("/me")
def update_my_profile(
    payload: ProfileUpdate,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)
    profile = _ensure_profile(current_citizen)
    metadata = dict(profile.profile_metadata or {})

    if "preferred_language_code" in changes:
        language = db.scalar(
            select(Language).where(
                Language.code == changes["preferred_language_code"],
                Language.is_active.is_(True),
            )
        )
        if language is None:
            raise HTTPException(
                status_code=422,
                detail="The selected language is not available.",
            )
        current_citizen.preferred_language_code = language.code

    for field in ("display_name",):
        if field in changes:
            setattr(profile, field, changes[field])

    if "date_of_birth" in changes:
        value = changes["date_of_birth"]
        profile.date_of_birth = (
            datetime.combine(value, time.min) if value is not None else None
        )

    for key in ("state_id", "district_id"):
        if key in changes:
            metadata[key] = str(changes[key]) if changes[key] else None

    state_id = metadata.get("state_id")
    district_id = metadata.get("district_id")
    state = db.get(Location, UUID(state_id)) if state_id else None
    district = db.get(Location, UUID(district_id)) if district_id else None
    if state_id and (
        state is None
        or state.location_type.lower() not in {"state", "union_territory"}
    ):
        raise HTTPException(status_code=422, detail="Selected state is invalid.")
    if district_id and (
        district is None
        or district.location_type.lower() != "district"
        or (state_id and district.parent_id != state.id)
    ):
        raise HTTPException(status_code=422, detail="Selected district is invalid for this state.")

    if "notification_preferences" in changes:
        preferences = changes["notification_preferences"] or {}
        if not set(preferences).issubset(NOTIFICATION_KEYS):
            raise HTTPException(
                status_code=422,
                detail="Unsupported notification preference.",
            )
        metadata["notification_preferences"] = preferences

    if "accessibility_preferences" in changes:
        preferences = changes["accessibility_preferences"]
        metadata["accessibility_preferences"] = (
            AccessibilityPreferences.model_validate(preferences).model_dump()
            if preferences is not None
            else {}
        )

    profile.profile_metadata = metadata
    db.commit()
    db.refresh(current_citizen)
    return _profile_response(current_citizen)


def _conversation_for_user(
    db: Session,
    conversation_id: UUID,
    user_id: UUID,
) -> ConversationSession:
    conversation = db.scalar(
        select(ConversationSession).where(
            ConversationSession.id == conversation_id,
            ConversationSession.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.get("/me/conversations")
def list_my_conversations(
    status_filter: str = Query("active", alias="status", pattern="^(active|archived|all)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    query = select(ConversationSession).where(
        ConversationSession.user_id == current_citizen.id
    )
    if status_filter != "all":
        query = query.where(ConversationSession.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ConversationSession.started_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(item.id),
                "title": item.title,
                "language_code": item.language_code,
                "status": item.status,
                "started_at": item.started_at.isoformat(),
            }
            for item in rows
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.post("/me/conversations", status_code=status.HTTP_201_CREATED)
def create_my_conversation(
    payload: ConversationCreate,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    language_code = (payload.language_code or current_citizen.preferred_language_code).lower()
    language = db.scalar(
        select(Language).where(
            Language.code == language_code,
            Language.is_active.is_(True),
        )
    )
    if language is None:
        raise HTTPException(status_code=422, detail="The selected language is not available.")
    conversation = ConversationSession(
        user_id=current_citizen.id,
        title=payload.title.strip() if payload.title else None,
        language_code=language.code,
        status="active",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"id": str(conversation.id), "title": conversation.title, "status": conversation.status}


@router.get("/me/conversations/{conversation_id}")
def get_my_conversation(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    conversation = _conversation_for_user(db, conversation_id, current_citizen.id)
    message_query = select(ConversationMessage).where(
        ConversationMessage.conversation_id == conversation.id
    )
    total = db.scalar(select(func.count()).select_from(message_query.subquery())) or 0
    messages = db.scalars(
        message_query.order_by(ConversationMessage.message_index)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "language_code": conversation.language_code,
        "status": conversation.status,
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "language_code": message.language_code,
                "grounded": (
                    (message.message_metadata or {}).get("grounded")
                    if message.role == "assistant"
                    else None
                ),
                "citations": (
                    (message.message_metadata or {}).get("citations", [])
                    if message.role == "assistant"
                    else []
                ),
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.patch("/me/conversations/{conversation_id}")
def rename_my_conversation(
    conversation_id: UUID,
    payload: ConversationRename,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    conversation = _conversation_for_user(db, conversation_id, current_citizen.id)
    conversation.title = payload.title
    db.commit()
    return {"id": str(conversation.id), "title": conversation.title}


@router.post("/me/conversations/{conversation_id}/archive")
def archive_my_conversation(
    conversation_id: UUID,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    conversation = _conversation_for_user(db, conversation_id, current_citizen.id)
    if conversation.status != "archived":
        conversation.status = "archived"
        conversation.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    return {"id": str(conversation.id), "status": conversation.status}


def _current_published_service(db: Session, service_id: UUID):
    return (
        published_service_query(db, "en")
        .filter(
            Service.id == service_id,
            Service.is_active.is_(True),
            Service.status == "active",
        )
        .first()
    )


def _saved_service_payload(
    service,
    version,
    title,
    description,
    application_url,
    translation_available,
):
    return {
        "service_id": str(service.id),
        "code": service.code,
        "slug": service.slug,
        "title": title,
        "description": description,
        "application_url": application_url,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "translation_available": translation_available,
    }


@router.get("/me/saved-services")
def list_saved_services(
    language: str = Query("en", min_length=2, max_length=10),
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    rows = (
        published_service_query(db, language)
        .join(SavedService, SavedService.service_id == Service.id)
        .filter(SavedService.user_id == current_citizen.id)
        .order_by(Service.code)
        .all()
    )
    return {
        "items": [
            _saved_service_payload(*row)
            for row in rows
        ],
        "total": len(rows),
    }


@router.put("/me/saved-services/{service_id}")
def save_service(
    service_id: UUID,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    row = _current_published_service(db, service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Published service not found.")
    saved = db.scalar(
        select(SavedService).where(
            SavedService.user_id == current_citizen.id,
            SavedService.service_id == service_id,
        )
    )
    if saved is None:
        db.add(SavedService(user_id=current_citizen.id, service_id=service_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    service, version, title, description, application_url, translation_available = row
    return _saved_service_payload(
        service,
        version,
        title,
        description,
        application_url,
        translation_available,
    )


@router.delete("/me/saved-services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_service(
    service_id: UUID,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    saved = db.scalar(
        select(SavedService).where(
            SavedService.user_id == current_citizen.id,
            SavedService.service_id == service_id,
        )
    )
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved service not found.")
    db.delete(saved)
    db.commit()
    return None


def _validate_application_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported citizen-recorded application status.")
    return normalized


def _build_checklist(
    db: Session,
    version_id: UUID,
    requested: list[ChecklistItemUpdate] | None,
) -> list[dict[str, Any]]:
    documents = db.scalars(
        select(RequiredDocument)
        .where(RequiredDocument.service_version_id == version_id)
        .order_by(RequiredDocument.display_order, RequiredDocument.created_at)
    ).all()
    document_map = {item.id: item for item in documents}
    if requested is None:
        return [
            {
                "document_id": str(item.id),
                "completed": False,
                "is_mandatory": item.is_mandatory,
            }
            for item in documents
        ]
    requested_ids = [item.document_id for item in requested]
    if len(set(requested_ids)) != len(requested_ids) or not set(requested_ids).issubset(document_map):
        raise HTTPException(
            status_code=422,
            detail="Checklist entries must refer to distinct documents in the published service version.",
        )
    return [
        {
            "document_id": str(item.document_id),
            "completed": item.completed,
            "is_mandatory": document_map[item.document_id].is_mandatory,
        }
        for item in requested
    ]


def _application_response(application: CitizenApplication) -> dict[str, Any]:
    return {
        "id": str(application.id),
        "service": {
            "id": str(application.service.id),
            "code": application.service.code,
            "slug": application.service.slug,
        },
        "service_id": str(application.service_id),
        "service_version_id": str(application.service_version_id),
        "service_version_number": application.service_version.version_number,
        "reference_number": application.reference_number,
        "application_date": (
            application.application_date.isoformat()
            if application.application_date
            else None
        ),
        "status": application.status,
        "status_source": "citizen_recorded",
        "notes": application.notes,
        "document_checklist": application.document_checklist,
        "status_history": [
            {
                "previous_status": item.previous_status,
                "status": item.new_status,
                "status_source": "citizen_recorded",
                "changed_at": item.changed_at.isoformat(),
            }
            for item in application.status_history
        ],
    }


def _application_for_user(
    db: Session,
    application_id: UUID,
    user_id: UUID,
) -> CitizenApplication:
    application = db.scalar(
        select(CitizenApplication).where(
            CitizenApplication.id == application_id,
            CitizenApplication.user_id == user_id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    return application


@router.post("/me/applications", status_code=status.HTTP_201_CREATED)
def create_application_record(
    payload: ApplicationCreate,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    row = _current_published_service(db, payload.service_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Published service not found.")
    service, version, _, _, _, _ = row
    application_date = payload.application_date
    if application_date and application_date > date.today():
        raise HTTPException(status_code=422, detail="Application date cannot be in the future.")

    application = CitizenApplication(
        user_id=current_citizen.id,
        service_id=service.id,
        service_version_id=version.id,
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
        application_date=application_date,
        status=payload.status,
        status_source="citizen_recorded",
        notes=payload.notes,
        document_checklist=_build_checklist(
            db,
            version.id,
            payload.document_checklist,
        ),
    )
    application.status_history.append(
        ApplicationStatusHistory(
            previous_status=None,
            new_status=application.status,
            status_source="citizen_recorded",
            changed_by_user_id=current_citizen.id,
        )
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return _application_response(application)


@router.get("/me/applications")
def list_application_records(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    query = select(CitizenApplication).where(
        CitizenApplication.user_id == current_citizen.id
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(CitizenApplication.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [_application_response(item) for item in rows],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


@router.get("/me/applications/{application_id}")
def get_application_record(
    application_id: UUID,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    return _application_response(
        _application_for_user(db, application_id, current_citizen.id)
    )


@router.patch("/me/applications/{application_id}")
def update_application_record(
    application_id: UUID,
    payload: ApplicationUpdate,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    application = _application_for_user(db, application_id, current_citizen.id)
    changes = payload.model_dump(exclude_unset=True)
    if "application_date" in changes:
        value = changes["application_date"]
        if value and value > date.today():
            raise HTTPException(status_code=422, detail="Application date cannot be in the future.")
        application.application_date = value
    if "reference_number" in changes:
        value = changes["reference_number"]
        application.reference_number = value.strip() if value else None
    if "notes" in changes:
        application.notes = changes["notes"]
    if "document_checklist" in changes:
        application.document_checklist = _build_checklist(
            db,
            application.service_version_id,
            changes["document_checklist"],
        )
    if "status" in changes and changes["status"] is not None:
        new_status = _validate_application_status(changes["status"])
        if new_status != application.status:
            application.status_history.append(
                ApplicationStatusHistory(
                    previous_status=application.status,
                    new_status=new_status,
                    status_source="citizen_recorded",
                    changed_by_user_id=current_citizen.id,
                )
            )
            application.status = new_status
            application.status_source = "citizen_recorded"
    db.commit()
    db.refresh(application)
    return _application_response(application)