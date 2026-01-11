from datetime import date
from typing import Optional
from enum import Enum
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey
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
# Week
# -----------------------------------
class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    start_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

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
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
