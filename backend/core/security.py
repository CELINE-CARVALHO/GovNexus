import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models.administration import AdminUser


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/admin/login"
)

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


def create_access_token(admin_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)

    payload = {
        "sub": str(admin_id),
        "token_type": "admin",
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired admin session.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        admin_id = payload.get("sub")
        token_type = payload.get("token_type")

        if not admin_id or token_type != "admin":
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

    if not admin or not admin.is_active:
        raise credentials_error

    return admin
