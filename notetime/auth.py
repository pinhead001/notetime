import base64
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

from notetime.db import SessionLocal, get_db
from notetime.models import User


# Configuration
class Settings(BaseSettings):
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def _hash_password_input(password: str) -> str:
    """First-pass SHA256 hash to handle passwords > 72 bytes, preserving full entropy"""
    # Get binary digest (32 bytes) and encode as base64 (~44 characters, well under 72 byte limit)
    binary_digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(binary_digest).decode('ascii')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Hash the input via SHA256, then verify against bcrypt hash
    sha256_hash = _hash_password_input(plain_password)
    return pwd_context.verify(sha256_hash, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using SHA256 first-pass, then bcrypt"""
    # First pass: SHA256 (handles any length, produces 64-char hex string)
    sha256_hash = _hash_password_input(password)
    # Second pass: bcrypt (now safely under 72 bytes)
    return pwd_context.hash(sha256_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> User:
    """Get the current authenticated user from JWT token (cookie or header)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie first, then from Authorization header
    token = None
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        # Cookie format is "Bearer <token>"
        if cookie_token.startswith("Bearer "):
            token = cookie_token[7:]
        else:
            token = cookie_token
    elif credentials:
        token = credentials.credentials

    if not token:
        # Redirect to login page for web UI requests
        from fastapi.responses import RedirectResponse

        if request.url.path.startswith("/api/"):
            raise credentials_exception
        else:
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                detail="Not authenticated",
                headers={"Location": "/auth/login"},
            )

    payload = decode_access_token(token)

    if payload is None:
        from fastapi.responses import RedirectResponse

        if request.url.path.startswith("/api/"):
            raise credentials_exception
        else:
            # Clear invalid cookie and redirect to login
            response = RedirectResponse(url="/auth/login", status_code=303)
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                detail="Invalid token",
                headers={"Location": "/auth/login"},
            )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """Return the current user if authenticated, or None for anonymous requests."""
    token = None
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        token = cookie_token[7:] if cookie_token.startswith("Bearer ") else cookie_token
    elif credentials:
        token = credentials.credentials

    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        return None

    return user
