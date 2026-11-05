import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models.administration import AdminUser
from backend.database.models.citizen import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/admin/login",
    auto_error=False,
)
citizen_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/citizen/login",
    auto_error=False,
)

CITIZEN_AUTH_COOKIE = "schemesathi_citizen_session"
ADMIN_AUTH_COOKIE = "schemesathi_admin_session"
ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS = 8 * 60 * 60

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64


def hash_password(password: str) -> str:
    """Hash a password using scrypt with a fresh random salt."""
    if not password or len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )

    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${salt.hex()}${derived_key.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        algorithm, n, r, p, salt_hex, key_hex = stored_hash.split("$")

        if algorithm != "scrypt":
            return False

        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)

        actual_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_key),
        )

        return hmac.compare_digest(actual_key, expected_key)
    except (ValueError, TypeError):
        return False


def create_access_token(admin_id: str, token_version: int = 0) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS
    )

    payload = {
        "sub": str(admin_id),
        "token_type": "admin",
        "token_version": token_version,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_citizen_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user.id),
        "token_type": "citizen",
        "token_version": user.auth_token_version,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def set_auth_cookie(
    response: Response,
    cookie_name: str,
    token: str,
    max_age: int,
) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=max_age,
        path=settings.API_V1_PREFIX,
        secure=not settings.DEBUG,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookie(response: Response, cookie_name: str) -> None:
    response.delete_cookie(
        key=cookie_name,
        path=settings.API_V1_PREFIX,
        secure=not settings.DEBUG,
        httponly=True,
        samesite="lax",
    )


def get_current_admin(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired admin session.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = token or request.cookies.get(ADMIN_AUTH_COOKIE)
    if token is None:
        raise credentials_error

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        admin_id = payload.get("sub")
        token_type = payload.get("token_type")
        token_version = payload.get("token_version")

        if (
            not admin_id
            or token_type != "admin"
            or not isinstance(token_version, int)
        ):
            raise credentials_error

        try:
            admin_id = UUID(str(admin_id))
        except (ValueError, TypeError):
            raise credentials_error

    except JWTError:
        raise credentials_error

    admin = db.scalar(
        select(AdminUser).where(AdminUser.id == admin_id)
    )

    if (
        not admin
        or not admin.is_active
        or admin.auth_token_version != token_version
    ):
        raise credentials_error

    return admin


def _decode_citizen_token(token: str) -> tuple[UUID, int]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("token_type") != "citizen":
            raise ValueError("Wrong token type.")
        user_id = UUID(str(payload.get("sub")))
        token_version = payload.get("token_version")
        if not isinstance(token_version, int):
            raise ValueError("Invalid token version.")
        return user_id, token_version
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired citizen session.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_citizen(
    request: Request,
    token: str | None = Depends(citizen_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = token or request.cookies.get(CITIZEN_AUTH_COOKIE)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Citizen authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id, token_version = _decode_citizen_token(token)
    user = db.scalar(select(User).where(User.id == user_id))
    if (
        user is None
        or user.account_status != "active"
        or user.auth_token_version != token_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired citizen session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_citizen(
    request: Request,
    token: str | None = Depends(citizen_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    token = token or request.cookies.get(CITIZEN_AUTH_COOKIE)
    if token is None:
        return None
    user_id, token_version = _decode_citizen_token(token)
    user = db.scalar(select(User).where(User.id == user_id))
    if (
        user is None
        or user.account_status != "active"
        or user.auth_token_version != token_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired citizen session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
