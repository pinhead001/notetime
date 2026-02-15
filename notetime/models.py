from datetime import date, datetime, time, timezone
from typing import Optional
from enum import Enum
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.orm import relationship, mapped_column, Mapped
from notetime.db import Base

# ---------------------------------------------------------------------------
# About ORM Models
# ---------------------------------------------------------------------------
# SQLAlchemy's ORM (Object-Relational Mapper) lets you work with database
# tables as Python classes. Each class here is a *model* — it maps directly
# to one table in the database:
#
#   Python class  →  DB table
#   instance      →  row
#   class attr    →  column
#
# The modern SQLAlchemy 2.0 syntax uses:
#   Mapped[type]         – declares a column's Python type
#   mapped_column(...)   – declares column constraints (PK, nullable, index…)
#   relationship(...)    – declares a link to rows in another table


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
# Using Python's Enum means you get auto-complete and typo-safety in code,
# while the DB stores just the string value (e.g. "active").
class TaskState(str, Enum):
    """Task lifecycle states per rules.md"""
    ACTIVE = "active"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    CANCELED = "canceled"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    # __tablename__ is required — it tells SQLAlchemy what to name the table
    # in the actual database.
    __tablename__ = "users"

    # primary_key=True  → this column is the unique row identifier (auto-increments)
    # init=False        → don't require this in __init__; the DB assigns it
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)

    # unique=True  → the DB enforces no two rows share the same value
    # index=True   → creates a DB index so lookups by email/username are fast
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    # We never store the raw password — only the hashed version.
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # insert_default=lambda: datetime.now(timezone.utc)  → DB/SQLAlchemy sets this automatically
    # on INSERT; we don't pass it in __init__.
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=lambda: datetime.now(timezone.utc), init=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships — not real columns; SQLAlchemy loads related rows on demand.
    #
    # back_populates="user"      → Week.user links back to this User object
    # cascade="all, delete-orphan" → if a User is deleted, all their Weeks
    #                                are deleted too (cascades down the tree:
    #                                Week → Task → WorkEntry)
    # default_factory=list       → initialise to [] in __init__ rather than
    #                                sharing a single list across instances
    # init=False                 → don't include in the dataclass __init__
    weeks: Mapped[list["Week"]] = relationship(
        "Week",
        back_populates="user",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )


# ---------------------------------------------------------------------------
# Week
# ---------------------------------------------------------------------------
class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)

    # ForeignKey("users.id") creates a DB-level foreign key constraint:
    # the value in this column must exist in users.id.
    # This is how we associate a row in one table with a row in another.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Always the Monday of the week (enforced by application logic, not DB).
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    scratchpad: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    # back_populates creates a two-way link:
    #   week.user   → the User that owns this week
    #   user.weeks  → all weeks belonging to that user
    user: Mapped["User"] = relationship("User", back_populates="weeks", init=False)
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="week",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Projects can be soft-deleted by setting is_active=False rather than
    # removing the row — this preserves historical task/time data.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="projects", init=False)
    # No cascade here — deleting a project doesn't delete its tasks;
    # tasks keep their project_id and the project name is just lost.
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", default_factory=list, init=False)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String, nullable=False)

    # Every task belongs to exactly one week.
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=False)

    # State is stored as a plain string ("active", "completed", etc.) rather
    # than an integer code, so the DB is readable without a lookup table.
    state: Mapped[str] = mapped_column(String, default=TaskState.ACTIVE.value)

    # Priority is an integer (1 = highest). Lower number = more urgent.
    priority: Mapped[int] = mapped_column(Integer, default=3)

    # Optional FK — a task doesn't have to belong to a project.
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, default=None)

    # delegate stores a person's name as a plain string (not a User FK).
    delegate: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    # Optional parent task for subtask hierarchy.
    parent_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, default=None)

    # Explicit ordering within the week; lower value = higher in the list.
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    week: Mapped["Week"] = relationship("Week", back_populates="tasks", init=False)
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks", init=False)

    # cascade="all, delete-orphan" → deleting a task removes all its work entries
    work_entries: Mapped[list["WorkEntry"]] = relationship(
        "WorkEntry",
        back_populates="task",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )


# ---------------------------------------------------------------------------
# WorkEntry
# ---------------------------------------------------------------------------
# A WorkEntry is a single time-log record: "I worked N minutes on task X
# on date Y".  Multiple entries can exist for the same task on the same day;
# the summary functions add them up before rounding.
class WorkEntry(Base):
    __tablename__ = "work_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Stored as raw minutes (no rounding at this level).
    # Rounding happens in time_engine.py when generating the summary.
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    # Optional clock times for display (e.g. "9:00 – 11:00").
    # These are informational only; minutes is the authoritative duration.
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True, default=None)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True, default=None)

    task: Mapped["Task"] = relationship("Task", back_populates="work_entries", init=False)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
# Stores user-submitted beta feedback. Not linked to the task/week system —
# it's a separate feature for collecting product feedback.
class Feedback(Base):
    __tablename__ = "feedback"

    # Required fields first (no defaults) — order matters for the dataclass
    # __init__ generated by MappedAsDataclass: fields without defaults must
    # come before fields with defaults.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    # Optional fields with defaults
    # user_id is nullable — feedback can be submitted anonymously (no login).
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, default=None)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    browser_info: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    reproducibility: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    # Tracks triage status of this feedback item (new → acknowledged → resolved…)
    status: Mapped[str] = mapped_column(String, default="new")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, insert_default=lambda: datetime.now(timezone.utc), init=False)
