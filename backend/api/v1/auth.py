from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.security import (
    CITIZEN_AUTH_COOKIE,
    clear_auth_cookie,
    create_citizen_access_token,
    get_current_citizen,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from backend.config import settings
from backend.database.connection import get_db
from backend.database.models.citizen import User, UserProfile
from backend.database.models.language import Language


router = APIRouter(prefix="/auth/citizen", tags=["Citizen Authentication"])


class CitizenRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, min_length=7, max_length=30)
    preferred_language_code: str = Field(default="en", min_length=2, max_length=10)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name is required.")
        return value

    @field_validator("phone_number")
    @classmethod
    def trim_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("preferred_language_code")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().lower()


class CitizenLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=256)


def _citizen_summary(user: User) -> dict[str, Any]:
    metadata = user.profile.profile_metadata if user.profile else {}
    accessibility_preferences = {
        "font_size": "medium",
        "text_scale_percent": 100,
        "high_contrast": False,
        "increased_spacing": False,
        "large_buttons": False,
        "simple_mode": False,
        "read_aloud": False,
        "reduced_motion": False,
    }
    accessibility_preferences.update(
        (metadata or {}).get("accessibility_preferences") or {}
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.profile.display_name if user.profile else None,
        "preferred_language_code": user.preferred_language_code,
        "accessibility_preferences": accessibility_preferences,
    }


def _token_response(user: User) -> dict:
    return {
        "access_token": create_citizen_access_token(user),
        "token_type": "bearer",
        "citizen": _citizen_summary(user),
    }


def _issue_citizen_session(response: Response, user: User) -> dict:
    result = _token_response(user)
    set_auth_cookie(
        response,
        CITIZEN_AUTH_COOKIE,
        result["access_token"],
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return result


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_citizen(
    payload: CitizenRegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    language = db.scalar(
        select(Language).where(
            Language.code == payload.preferred_language_code,
            Language.is_active.is_(True),
        )
    )
    if language is None:
        raise HTTPException(
            status_code=422,
            detail="The selected language is not available.",
        )

    if db.scalar(
        select(User.id).where(func.lower(User.email) == payload.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if payload.phone_number and db.scalar(
        select(User.id).where(User.phone_number == payload.phone_number)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        )

    user = User(
        email=payload.email,
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        account_status="active",
        preferred_language_code=language.code,
        email_verified=False,
        phone_verified=False,
    )
    user.profile = UserProfile(display_name=payload.display_name)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with the supplied email or phone number already exists.",
        ) from exc

    return _issue_citizen_session(response, user)


@router.post("/login")
def login_citizen(
    payload: CitizenLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(func.lower(User.email) == str(payload.email).lower())
    )
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This citizen account is not active.",
        )

    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return _issue_citizen_session(response, user)


@router.post("/logout")
def logout_citizen(
    response: Response,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    current_citizen.auth_token_version += 1
    db.commit()
    clear_auth_cookie(response, CITIZEN_AUTH_COOKIE)
    return {"message": "All active citizen sessions have been invalidated."}


@router.post("/password")
def change_citizen_password(
    payload: PasswordChangeRequest,
    response: Response,
    current_citizen: User = Depends(get_current_citizen),
    db: Session = Depends(get_db),
):
    if not current_citizen.password_hash or not verify_password(
        payload.current_password,
        current_citizen.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The new password must differ from the current password.",
        )

    current_citizen.password_hash = hash_password(payload.new_password)
    current_citizen.auth_token_version += 1
    db.commit()
    return _issue_citizen_session(response, current_citizen)