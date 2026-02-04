from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel, field_validator, ConfigDict

# ------------------------------
# Task input
# ------------------------------
class TaskCreate(BaseModel):
    title: str
    week_id: int
    state: str = "active"
    priority: int = 1
    project_id: Optional[int] = None
    delegate: Optional[str] = None
    parent_task_id: Optional[int] = None
    sort_order: int = 0


class TaskUpdate(BaseModel):
    """Task update schema - all fields optional"""
    title: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[int] = None
    delegate: Optional[str] = None
    parent_task_id: Optional[int] = None
    sort_order: Optional[int] = None

# ------------------------------
# Project input
# ------------------------------
class ProjectUpdate(BaseModel):
    """Project update schema - all fields optional"""
    name: Optional[str] = None
    is_active: Optional[bool] = None


# ------------------------------
# WorkEntry input
# ------------------------------
class WorkEntryCreate(BaseModel):
    task_id: int
    date: date
    minutes: int
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    note: str | None = None

    @field_validator("minutes")
    @classmethod
    def positive_minutes(cls, v):
        if v <= 0:
            raise ValueError("Minutes must be positive")
        return v


class WorkEntryUpdate(BaseModel):
    """WorkEntry update schema - all fields optional"""
    date: Optional[date] = None
    start_time: Optional[str] = None  # Accept as string for easier parsing
    end_time: Optional[str] = None    # Accept as string for easier parsing
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
    parent_task_id: Optional[int] = None
    sort_order: int = 0


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
    start_time: Optional[time] = None
    end_time: Optional[time] = None
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
