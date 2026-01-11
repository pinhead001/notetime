from datetime import date
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from dataclasses import dataclass
# from notetime.db import Base

# -----------------------------------
# Week
# -----------------------------------
# class Week(Base):

class Week:
    __tablename__ = "weeks"

    id = mapped_column(Integer, primary_key=True)
    start_date = mapped_column(Date, unique=True, nullable=False)
    note = mapped_column(String, nullable=True)

    tasks = relationship(
        "Task",
        back_populates="week",
        cascade="all, delete-orphan"
    )

# -----------------------------------
# Project
# -----------------------------------
# class Project(Base):

class Project:
    __tablename__ = "projects"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, unique=True, nullable=False)
    is_active = mapped_column(Boolean, default=True)

    tasks = relationship("Task", back_populates="project")

# -----------------------------------
# Task
# -----------------------------------
# class Task(Base):

class Task:
    __tablename__ = "tasks"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String, nullable=False)
    priority = mapped_column(Integer, default=3)

    week_id = mapped_column(ForeignKey("weeks.id"), nullable=False)
    project_id = mapped_column(ForeignKey("projects.id"), nullable=True)

    week = relationship("Week", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    work_entries = relationship(
        "WorkEntry",
        back_populates="task",
        cascade="all, delete-orphan"
    )

# -----------------------------------
# WorkEntry
# -----------------------------------
# class WorkEntry(Base):

class WorkEntry:
    __tablename__ = "work_entries"

    id = mapped_column(Integer, primary_key=True)
    task_id = mapped_column(ForeignKey("tasks.id"), nullable=False)
    date = mapped_column(Date, nullable=False)
    minutes = mapped_column(Integer, nullable=False)
    note = mapped_column(String, nullable=True)

    task = relationship("Task", back_populates="work_entries")

# -----------------------------------
# TaskSummary
# -----------------------------------

@dataclass(frozen=True)
class TaskSummary:
    task_id: str
    task_name: str
    total_minutes: int