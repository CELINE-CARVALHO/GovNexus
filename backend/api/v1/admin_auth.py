from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models.administration import AdminUser
from backend.core.security import (
    ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS,
    ADMIN_AUTH_COOKIE,
    clear_auth_cookie,
    create_access_token,
    get_current_admin,
    set_auth_cookie,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str
    admin: dict


@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(
    payload: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    admin = db.scalar(
        select(AdminUser).where(
            AdminUser.email == str(payload.email).lower()
        )
    )

    # Use the same error for unknown accounts and incorrect passwords.
    if (
        not admin
        or not admin.is_active
        or not verify_password(payload.password, admin.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    from datetime import datetime, timezone

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(str(admin.id), admin.auth_token_version)
    set_auth_cookie(
        response,
        ADMIN_AUTH_COOKIE,
        token,
        ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": {
            "id": str(admin.id),
            "email": admin.email,
            "full_name": admin.full_name,
            "role": admin.role,
        },
    }


@router.post("/admin/logout")
def admin_logout(
    response: Response,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    current_admin.auth_token_version += 1
    db.commit()
    clear_auth_cookie(response, ADMIN_AUTH_COOKIE)
    return {"message": "Administrator session revoked."}
