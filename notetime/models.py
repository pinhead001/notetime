from datetime import date, datetime
from typing import Optional
from enum import Enum
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped
from notetime.db import Base

# -----------------------------------
# Enums
# -----------------------------------
class TaskState(str, Enum):
    """Task lifecycle states per rules.md"""
    ACTIVE = "active"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    CANCELED = "canceled"

# -----------------------------------
# User
# -----------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, init=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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

# -----------------------------------
# Week
# -----------------------------------
class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    user: Mapped["User"] = relationship("User", back_populates="weeks", init=False)
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="week",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )

# -----------------------------------
# Project
# -----------------------------------
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="projects", init=False)
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", default_factory=list, init=False)

# -----------------------------------
# Task
# -----------------------------------
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=False)

    state: Mapped[str] = mapped_column(String, default=TaskState.ACTIVE.value)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, default=None)
    delegate: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    week: Mapped["Week"] = relationship("Week", back_populates="tasks", init=False)
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks", init=False)
    work_entries: Mapped[list["WorkEntry"]] = relationship(
        "WorkEntry",
        back_populates="task",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False
    )

# -----------------------------------
# WorkEntry
# -----------------------------------
class WorkEntry(Base):
    __tablename__ = "work_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    task: Mapped["Task"] = relationship("Task", back_populates="work_entries", init=False)


# -----------------------------------
# Feedback
# -----------------------------------
class Feedback(Base):
    __tablename__ = "feedback"

    # Required fields first (no defaults)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # Optional fields with defaults
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, default=None)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    browser_info: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    reproducibility: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String, default="new")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, init=False)
