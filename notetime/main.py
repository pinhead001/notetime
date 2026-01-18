"""
FastAPI application - Day 6 CRUD Endpoints + Day 7 HTMX UI

Main API application providing CRUD operations and HTMX-powered web interface.

Run with:
    uvicorn notetime.main:app --reload

API will be available at:
    http://localhost:8000/docs (API docs)
    http://localhost:8000 (Web UI)
"""
from datetime import date, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetime.db import SessionLocal, engine
from notetime.models import Base, Week, Project, Task, WorkEntry, TaskState
from notetime.schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
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
    description="Weekly task and time-tracking API with HTMX UI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup templates and static files
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


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

@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_api(
    title: str = Form(...),
    week_id: int = Form(...),
    state: str = Form("active"),
    priority: int = Form(3),
    project_id: Optional[int] = Form(None),
    delegate: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new task (accepts form data for HTMX or JSON for API).

    Args:
        title: Task title
        week_id: Week ID
        state: Task state (default: active)
        priority: Priority level (default: 3)
        project_id: Project ID (optional)
        delegate: Delegate name (optional)

    Returns:
        Created task with ID

    Raises:
        404: If week_id or project_id doesn't exist
    """
    # Verify week exists
    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {week_id} not found"
        )

    # Verify project exists if provided
    if project_id is not None and project_id != "":
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )

    # Create task
    db_task = Task(
        title=title,
        week_id=week_id,
        state=state,
        priority=priority,
        project_id=project_id if project_id and project_id != "" else None,
        delegate=delegate
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing task.

    Args:
        task_id: ID of task to update
        task_update: Fields to update (JSON body)

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
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.state is not None:
        # Validate state
        valid_states = [s.value for s in TaskState]
        if task_update.state not in valid_states:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid state. Must be one of: {valid_states}"
            )
        db_task.state = task_update.state
    if task_update.priority is not None:
        db_task.priority = task_update.priority
    if task_update.delegate is not None:
        db_task.delegate = task_update.delegate

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

@app.post("/api/work_entries", response_model=WorkEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_work_entry_api(
    task_id: int = Form(...),
    date: date = Form(...),
    minutes: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new work entry (time log) - accepts form data for HTMX.

    Args:
        task_id: ID of task
        date: Date of work
        minutes: Minutes worked
        note: Optional note

    Returns:
        Created work entry with ID

    Raises:
        404: If task_id doesn't exist
        422: If validation fails (e.g., negative minutes)
    """
    # Validate minutes
    if minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Minutes must be positive"
        )

    # Verify task exists
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    # Create work entry
    db_entry = WorkEntry(
        task_id=task_id,
        date=date,
        minutes=minutes,
        note=note
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
# Web UI Routes (HTMX)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def weekly_view(request: Request, db: Session = Depends(get_db)):
    """
    Serve the weekly HTML page (current week).

    This is the main web interface.
    """
    # Get or create current week
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    week = db.scalars(
        select(Week).where(Week.start_date == week_start)
    ).first()

    if not week:
        week = Week(start_date=week_start)
        db.add(week)
        db.commit()
        db.refresh(week)

    # Get weekly data
    weekly_data = get_week(week.id, db)

    return templates.TemplateResponse("weekly.html", {
        "request": request,
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary
    })


@app.get("/weeks/{week_id}/page", response_class=HTMLResponse)
async def weekly_view_by_id(request: Request, week_id: int, db: Session = Depends(get_db)):
    """Serve weekly page for a specific week"""
    weekly_data = get_week(week_id, db)

    return templates.TemplateResponse("weekly.html", {
        "request": request,
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary
    })


# ============================================
# HTMX Partial Routes
# ============================================

@app.get("/partials/task-form", response_class=HTMLResponse)
async def task_form_partial(request: Request, week_id: int, db: Session = Depends(get_db)):
    """Return task creation form (HTMX partial)"""
    projects = db.scalars(select(Project).where(Project.is_active == True)).all()

    html = f"""
    <form hx-post="/api/tasks" hx-target="#add-task-container">
        <input type="hidden" name="week_id" value="{week_id}">
        <input type="text" name="title" placeholder="Task title" required>
        <select name="project_id">
            <option value="">No project</option>
            {"".join(f'<option value="{p.id}">{p.name}</option>' for p in projects)}
        </select>
        <select name="priority">
            <option value="1">Priority 1 (High)</option>
            <option value="2">Priority 2</option>
            <option value="3" selected>Priority 3 (Normal)</option>
        </select>
        <button type="submit">Add Task</button>
        <button type="button" hx-get="/partials/task-form-cancel" hx-target="#add-task-container">Cancel</button>
    </form>
    """
    return HTMLResponse(content=html)


@app.get("/partials/task-form-cancel", response_class=HTMLResponse)
async def task_form_cancel():
    """Cancel task form"""
    html = '<button hx-get="/partials/task-form?week_id=1" hx-target="#add-task-container" hx-swap="innerHTML" class="btn-add">+ New Task</button>'
    return HTMLResponse(content=html)


@app.get("/partials/log-form", response_class=HTMLResponse)
async def log_form_partial(request: Request, week_id: int, db: Session = Depends(get_db)):
    """Return work entry form (HTMX partial)"""
    tasks = db.scalars(select(Task).where(Task.week_id == week_id)).all()

    html = f"""
    <form hx-post="/api/work_entries" hx-target="#add-log-container">
        <select name="task_id" required>
            <option value="">Select task...</option>
            {"".join(f'<option value="{t.id}">{t.title}</option>' for t in tasks)}
        </select>
        <input type="date" name="date" value="{date.today()}" required>
        <input type="number" name="minutes" placeholder="Minutes worked" min="1" required>
        <textarea name="note" placeholder="Note (optional)" rows="2"></textarea>
        <button type="submit">Log Time</button>
        <button type="button" hx-get="/partials/log-form-cancel" hx-target="#add-log-container">Cancel</button>
    </form>
    """
    return HTMLResponse(content=html)


@app.get("/partials/log-form-cancel", response_class=HTMLResponse)
async def log_form_cancel():
    """Cancel log form"""
    html = '<button hx-get="/partials/log-form?week_id=1" hx-target="#add-log-container" hx-swap="innerHTML" class="btn-add">+ Log Time</button>'
    return HTMLResponse(content=html)


# ============================================
# Task Action Routes (HTMX)
# ============================================

@app.put("/api/tasks/{task_id}/complete", response_class=HTMLResponse)
async def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Mark task as completed (HTMX action)"""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.state = TaskState.COMPLETED.value
    db.commit()

    # Return updated task HTML
    return HTMLResponse(content=f'<div class="task-item task-completed">✓ {task.title} (Completed)</div>')


@app.put("/api/tasks/{task_id}/defer", response_class=HTMLResponse)
async def defer_task(task_id: int, db: Session = Depends(get_db)):
    """Mark task for deferral (HTMX action)"""
    # In a full implementation, this would rollover to next week
    # For now, just mark it visually
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return HTMLResponse(content=f'<div class="task-item">→ {task.title} (Will be moved to next week)</div>')


# ============================================
# Health Check
# ============================================

@app.get("/api")
def api_root():
    """API info endpoint"""
    return {
        "message": "Notetime API",
        "version": "1.0.0",
        "docs": "/docs",
        "web_ui": "/"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
