from datetime import date
from typing import Optional, List
from pydantic import BaseModel, field_validator, ConfigDict

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
