from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, field_validator, ConfigDict, EmailStr

# ========================================
# Authentication Schemas
# ========================================

# ------------------------------
# User registration
# ------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

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
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
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
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------------------
# User response
# ------------------------------
class UserResponse(BaseModel):
    """User data returned by API"""
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
    week_id: int
    state: str = "active"
    priority: int = 3
    project_id: Optional[int] = None
    delegate: Optional[str] = None

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
