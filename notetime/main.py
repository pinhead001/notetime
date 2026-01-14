"""
FastAPI application - Day 6 CRUD Endpoints

Main API application providing CRUD operations for tasks, work entries, and weekly views.

Run with:
    uvicorn notetime.main:app --reload

API will be available at:
    http://localhost:8000
    Docs: http://localhost:8000/docs
"""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetime.db import SessionLocal, engine
from notetime.models import Base, Week, Project, Task, WorkEntry, TaskState
from notetime.schemas import (
    TaskCreate, TaskResponse,
    WorkEntryCreate, WorkEntryResponse,
    WeekResponse, WeeklyView,
    ProjectResponse
)
from notetime.summary import generate_weekly_summary


# Create database tables
Base.metadata.create_all(bind=engine)


# Initialize FastAPI app
app = FastAPI(
    title="Notetime API",
    description="Weekly task and time-tracking API",
    version="1.0.0"
)


# Dependency to get database session
def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# Task Endpoints
# ============================================

@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.

    Args:
        task: Task data (title, week_id, state, priority, project_id, delegate)

    Returns:
        Created task with ID

    Raises:
        404: If week_id or project_id doesn't exist
        422: If validation fails
    """
    # Verify week exists
    week = db.get(Week, task.week_id)
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {task.week_id} not found"
        )

    # Verify project exists if provided
    if task.project_id is not None:
        project = db.get(Project, task.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {task.project_id} not found"
            )

    # Create task
    db_task = Task(
        title=task.title,
        week_id=task.week_id,
        state=task.state,
        priority=task.priority,
        project_id=task.project_id,
        delegate=task.delegate
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    title: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[int] = None,
    delegate: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update an existing task.

    Args:
        task_id: ID of task to update
        title: New title (optional)
        state: New state (optional)
        priority: New priority (optional)
        delegate: New delegate (optional)

    Returns:
        Updated task

    Raises:
        404: If task not found
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Update fields if provided
    if title is not None:
        db_task.title = title
    if state is not None:
        # Validate state
        valid_states = [s.value for s in TaskState]
        if state not in valid_states:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid state. Must be one of: {valid_states}"
            )
        db_task.state = state
    if priority is not None:
        db_task.priority = priority
    if delegate is not None:
        db_task.delegate = delegate

    db.commit()
    db.refresh(db_task)

    return db_task


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    Get a specific task by ID.

    Args:
        task_id: ID of task to retrieve

    Returns:
        Task details

    Raises:
        404: If task not found
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    return db_task


# ============================================
# Work Entry Endpoints
# ============================================

@app.post("/work_entries", response_model=WorkEntryResponse, status_code=status.HTTP_201_CREATED)
def create_work_entry(entry: WorkEntryCreate, db: Session = Depends(get_db)):
    """
    Create a new work entry (time log).

    Args:
        entry: Work entry data (task_id, date, minutes, note)

    Returns:
        Created work entry with ID

    Raises:
        404: If task_id doesn't exist
        422: If validation fails (e.g., negative minutes)
    """
    # Verify task exists
    task = db.get(Task, entry.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {entry.task_id} not found"
        )

    # Create work entry
    db_entry = WorkEntry(
        task_id=entry.task_id,
        date=entry.date,
        minutes=entry.minutes,
        note=entry.note
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return db_entry


@app.get("/work_entries/{entry_id}", response_model=WorkEntryResponse)
def get_work_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Get a specific work entry by ID.

    Args:
        entry_id: ID of work entry to retrieve

    Returns:
        Work entry details

    Raises:
        404: If work entry not found
    """
    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )

    return db_entry


# ============================================
# Week Endpoints
# ============================================

@app.post("/weeks", response_model=WeekResponse, status_code=status.HTTP_201_CREATED)
def create_week(start_date: date, note: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Create a new week.

    Args:
        start_date: Monday start date for the week
        note: Optional note for the week

    Returns:
        Created week with ID

    Raises:
        400: If week with this start_date already exists
    """
    # Check if week already exists
    existing = db.scalars(
        select(Week).where(Week.start_date == start_date)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week starting {start_date} already exists"
        )

    # Create week
    db_week = Week(start_date=start_date, note=note)
    db.add(db_week)
    db.commit()
    db.refresh(db_week)

    return db_week


@app.get("/weeks/current", response_model=WeeklyView)
def get_current_week(db: Session = Depends(get_db)):
    """
    Get the current week's data.

    Finds or creates the week starting on the most recent Monday.

    Returns:
        WeeklyView for current week
    """
    # Calculate current week's Monday
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    # Find or create week
    week = db.scalars(
        select(Week).where(Week.start_date == week_start)
    ).first()

    if not week:
        # Create the week if it doesn't exist
        week = Week(start_date=week_start)
        db.add(week)
        db.commit()
        db.refresh(week)

    # Return full weekly view
    return get_week(week.id, db)


@app.get("/weeks/{week_id}", response_model=WeeklyView)
def get_week(week_id: int, db: Session = Depends(get_db)):
    """
    Get complete weekly view including tasks, work entries, and summary.

    Args:
        week_id: ID of week to retrieve

    Returns:
        WeeklyView with week, tasks, work entries, projects, and summary

    Raises:
        404: If week not found
    """
    # Get week
    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {week_id} not found"
        )

    # Get all tasks for this week
    tasks = db.scalars(
        select(Task).where(Task.week_id == week_id)
    ).all()

    # Get all work entries for these tasks
    if tasks:
        task_ids = [task.id for task in tasks]
        work_entries = db.scalars(
            select(WorkEntry).where(WorkEntry.task_id.in_(task_ids))
        ).all()
    else:
        work_entries = []

    # Get all projects referenced by tasks
    project_ids = list(set(task.project_id for task in tasks if task.project_id is not None))
    if project_ids:
        projects = db.scalars(
            select(Project).where(Project.id.in_(project_ids))
        ).all()
    else:
        projects = []

    # Generate summary
    summary = generate_weekly_summary(week_id, db)

    return WeeklyView(
        week=WeekResponse.model_validate(week),
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        work_entries=[WorkEntryResponse.model_validate(e) for e in work_entries],
        projects=[ProjectResponse.model_validate(p) for p in projects],
        summary=summary
    )


# ============================================
# Project Endpoints
# ============================================

@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(name: str, is_active: bool = True, db: Session = Depends(get_db)):
    """
    Create a new project.

    Args:
        name: Project name (must be unique)
        is_active: Whether project is active (default: True)

    Returns:
        Created project with ID

    Raises:
        400: If project with this name already exists
    """
    # Check if project already exists
    existing = db.scalars(
        select(Project).where(Project.name == name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project '{name}' already exists"
        )

    # Create project
    db_project = Project(name=name, is_active=is_active)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@app.get("/projects", response_model=List[ProjectResponse])
def list_projects(active_only: bool = True, db: Session = Depends(get_db)):
    """
    List all projects.

    Args:
        active_only: If True, only return active projects (default: True)

    Returns:
        List of projects
    """
    query = select(Project)
    if active_only:
        query = query.where(Project.is_active == True)

    projects = db.scalars(query).all()
    return projects


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get a specific project by ID.

    Args:
        project_id: ID of project to retrieve

    Returns:
        Project details

    Raises:
        404: If project not found
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    return project


# ============================================
# Health Check
# ============================================

@app.get("/")
def root():
    """Health check / welcome endpoint"""
    return {
        "message": "Notetime API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
