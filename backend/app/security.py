"""Authentication, password hashing and role-based authorization.

Passwords use PBKDF2-HMAC-SHA256 from the standard library (no native build
dependencies). Tokens are short-lived JWTs signed with SECRET_KEY.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .constants import Role
from .db import get_db
from .models import User

PBKDF2_ITERATIONS = 240_000
_ALGO = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("password must not be empty")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[_ALGO])


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if user and user.is_active and verify_password(password, user.password_hash):
        return user
    return None


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _credentials_error()
    try:
        payload = decode_token(credentials.credentials)
    except Exception:  # noqa: BLE001 - any JWT failure is an auth failure
        raise _credentials_error() from None
    email = payload.get("sub")
    if not email:
        raise _credentials_error()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


def require_role(*roles: str):
    """Dependency factory enforcing that the caller holds one of ``roles``."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account does not have permission for this action.",
            )
        return user

    return _checker


require_admin = require_role(Role.ADMIN)
require_staff = require_role(Role.ADMIN, Role.REVIEWER)
