from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, field_validator, ConfigDict, EmailStr

# ---------------------------------------------------------------------------
# About Pydantic schemas
# ---------------------------------------------------------------------------
# Pydantic models (schemas) serve a different purpose than SQLAlchemy models:
#
#   SQLAlchemy model  – represents a DB table; used to read/write the database
#   Pydantic schema   – represents data shape for input validation or output
#                       serialisation; never touches the database directly
#
# Why separate schemas for input vs output?
#   - Input schemas validate incoming request data and reject bad values early
#     (wrong types, missing required fields, out-of-range numbers, etc.)
#   - Response schemas control exactly what fields are returned to the client —
#     e.g. we return UserResponse which omits hashed_password.
#
# The `from_attributes=True` config on response schemas tells Pydantic it can
# read values from SQLAlchemy ORM objects (which use attribute access) rather
# than plain dicts.

# ========================================
# Authentication Schemas
# ========================================

# ------------------------------
# User registration
# ------------------------------
class UserRegister(BaseModel):
    # EmailStr validates that the string looks like a valid email address.
    email: EmailStr
    username: str
    password: str

    # @field_validator runs after the field is parsed. It can raise ValueError
    # to reject the value, or return a (possibly modified) valid value.
    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ------------------------------
# User login
# ------------------------------
class UserLogin(BaseModel):
    username: str
    password: str


# ------------------------------
# Token response
# ------------------------------
# Returned after a successful login. The client stores access_token and sends
# it in the "Authorization: Bearer <token>" header on subsequent requests.
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------------------
# User response
# ------------------------------
class UserResponse(BaseModel):
    """User data returned by API — notably omits hashed_password."""
    # from_attributes=True lets Pydantic pull values from SQLAlchemy ORM
    # objects (e.g. user.email) instead of requiring a plain dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime
    is_active: bool


# ========================================
# Task Management Schemas
# ========================================

# ------------------------------
# Week input
# ------------------------------
class WeekCreate(BaseModel):
    # date type accepts "YYYY-MM-DD" strings and converts to Python date objects.
    start_date: date
    note: Optional[str] = None


# ------------------------------
# Project input
# ------------------------------
class ProjectCreate(BaseModel):
    name: str
    is_active: bool = True


# ------------------------------
# Task input
# ------------------------------
class TaskCreate(BaseModel):
    title: str
    week_id: int   # Must reference an existing Week that belongs to the user
    state: str = "active"
    priority: int = 3
    project_id: Optional[int] = None   # None = no project
    delegate: Optional[str] = None     # Free-text name of person task is delegated to


# ------------------------------
# WorkEntry input
# ------------------------------
class WorkEntryCreate(BaseModel):
    task_id: int
    date: date
    minutes: int
    note: str | None = None

    @field_validator("minutes")
    @classmethod
    def positive_minutes(cls, v):
        if v <= 0:
            raise ValueError("Minutes must be positive")
        return v


# Update schemas use all-Optional fields so the client only needs to send
# the fields they want to change (PATCH-style semantics, even though we use PUT).
class WeekUpdate(BaseModel):
    note: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[int] = None
    delegate: Optional[str] = None


class WorkEntryUpdate(BaseModel):
    minutes: Optional[int] = None
    note: Optional[str] = None


# ------------------------------
# Task summary output
# ------------------------------
class TaskSummary(BaseModel):
    title: str
    total_minutes: int


# ========================================
# Response Schemas (for API output)
# ========================================
# All response schemas have model_config = ConfigDict(from_attributes=True)
# so FastAPI can convert SQLAlchemy ORM objects → JSON automatically.

# ------------------------------
# Week response
# ------------------------------
class WeekResponse(BaseModel):
    """Week data returned by API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    note: Optional[str] = None


# ------------------------------
# Project response
# ------------------------------
class ProjectResponse(BaseModel):
    """Project data returned by API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool


# ------------------------------
# Task response
# ------------------------------
class TaskResponse(BaseModel):
    """Task data returned by API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    week_id: int
    state: str
    priority: int
    project_id: Optional[int] = None
    delegate: Optional[str] = None


# ------------------------------
# WorkEntry response
# ------------------------------
class WorkEntryResponse(BaseModel):
    """WorkEntry data returned by API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    date: date
    minutes: int
    note: Optional[str] = None


# ------------------------------
# Weekly view (composite)
# ------------------------------
# This is a "view model" — it combines several related objects into one
# response so the frontend can render the full page with a single API call
# instead of making separate requests for tasks, work entries, etc.
class WeeklyView(BaseModel):
    """Complete weekly view for frontend"""
    week: WeekResponse
    projects: List[ProjectResponse]
    tasks: List[TaskResponse]
    work_entries: List[WorkEntryResponse]
    summary: dict  # Output from time_engine.summarize_by_project


# ========================================
# Feedback Schemas
# ========================================

# Literal[...] restricts the field to only those exact string values.
# Pydantic will reject anything not in the list.
FeedbackCategory = Literal["bug_report", "feature_request", "general", "ui_ux", "performance"]
FeedbackSeverity = Literal["critical", "high", "medium", "low"]
FeedbackReproducibility = Literal["always", "sometimes", "rarely", "na"]


class FeedbackCreate(BaseModel):
    category: FeedbackCategory
    title: str
    description: str
    rating: Optional[int] = None
    contact_email: Optional[str] = None
    browser_info: Optional[str] = None
    reproducibility: Optional[FeedbackReproducibility] = None
    severity: Optional[FeedbackSeverity] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        if len(v) > 200:
            raise ValueError("Title must be 200 characters or fewer")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


class FeedbackResponse(BaseModel):
    """Feedback data returned by API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    category: str
    title: str
    description: str
    rating: Optional[int] = None
    contact_email: Optional[str] = None
    reproducibility: Optional[str] = None
    severity: Optional[str] = None
    submitted_at: datetime
    status: str
