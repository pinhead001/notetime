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


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
# pydantic_settings.BaseSettings reads values from a .env file and/or from
# real environment variables (env vars override the .env file).
# This keeps secrets out of source code.
class Settings(BaseSettings):
    # SECRET_KEY is used to sign JWTs. Anyone who knows this key can forge
    # tokens, so in production it must be a long random string stored in an
    # environment variable — never committed to the repo.
    secret_key: str = "your-secret-key-change-this-in-production"

    # HS256 = HMAC-SHA256. The most common JWT signing algorithm.
    algorithm: str = "HS256"

    # Tokens expire after 7 days. After expiry the user must log in again.
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
# We use bcrypt (via passlib) because it's slow by design — brute-forcing
# it is expensive even if an attacker gets the hash database.
#
# CryptContext handles the bcrypt work: hashing and verifying passwords.
# deprecated="auto" means old hash formats are automatically re-hashed on
# the next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTPBearer parses the "Authorization: Bearer <token>" header that API
# clients send. Used below in get_current_user.
security = HTTPBearer()


def _hash_password_input(password: str) -> str:
    """First-pass SHA256 hash to handle passwords > 72 bytes, preserving full entropy"""
    # Why two passes?
    # bcrypt silently truncates inputs at 72 bytes. A long password would
    # be accepted but only the first 72 bytes would be checked — meaning
    # different long passwords could collide.
    #
    # Fix: SHA256 the password first. SHA256 always produces 32 bytes,
    # then base64-encode it to get a safe ASCII string (~44 chars, well
    # under the 72-byte limit). bcrypt then hashes that.
    binary_digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(binary_digest).decode('ascii')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Re-apply the same SHA256 first-pass, then let bcrypt compare.
    sha256_hash = _hash_password_input(plain_password)
    return pwd_context.verify(sha256_hash, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using SHA256 first-pass, then bcrypt"""
    sha256_hash = _hash_password_input(password)
    return pwd_context.hash(sha256_hash)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
# JWT (JSON Web Token) is a signed string that encodes claims — in our case,
# the user's ID. The signature prevents tampering: only the server (which
# knows SECRET_KEY) can produce a valid token.
#
# Token format:  <base64 header>.<base64 payload>.<signature>
# Payload here:  {"sub": "42", "exp": 1234567890}
#   sub = "subject" = user ID (conventionally a string)
#   exp = expiry timestamp (Unix epoch seconds)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Add the expiry claim to the payload before signing.
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        # jwt.decode() verifies the signature AND checks the exp claim.
        # Returns the payload dict if valid, raises JWTError if not.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Covers: bad signature, expired token, malformed token, etc.
        return None


# ---------------------------------------------------------------------------
# FastAPI dependency: get_current_user
# ---------------------------------------------------------------------------
# This function is used as a *dependency* in route handlers:
#
#   @app.get("/api/something")
#   def my_route(current_user: User = Depends(get_current_user)):
#       ...
#
# FastAPI calls get_current_user() automatically before the route runs.
# If it raises an HTTPException, the route never runs and the client gets
# the error response instead.
#
# Two places to find the token:
#   1. HTTP cookie "access_token" — set by the browser after the web login form
#   2. Authorization: Bearer <token> header — sent by API clients / curl
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)  # auto_error=False so we handle missing header ourselves
    ),
) -> User:
    """Get the current authenticated user from JWT token (cookie or header)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try cookie first (web browser), then Authorization header (API client).
    token = None
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        # Cookie is stored as "Bearer <token>" — strip the prefix.
        if cookie_token.startswith("Bearer "):
            token = cookie_token[7:]
        else:
            token = cookie_token
    elif credentials:
        token = credentials.credentials

    if not token:
        # No token found: redirect the browser to the login page, or return
        # 401 JSON for API requests (detected by URL prefix).
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
            # Token is invalid/expired — clear the bad cookie and send to login.
            response = RedirectResponse(url="/auth/login", status_code=303)
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                detail="Invalid token",
                headers={"Location": "/auth/login"},
            )

    # "sub" is the standard JWT claim for the subject (= user ID stored as string).
    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Look up the user in the DB to make sure they still exist and are active.
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


# ---------------------------------------------------------------------------
# Optional auth dependency
# ---------------------------------------------------------------------------
# Some endpoints (e.g. the feedback form) are accessible whether or not the
# user is logged in. This dependency works like get_current_user but returns
# None instead of raising an error when no valid token is found.
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
