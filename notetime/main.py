"""
FastAPI application - Day 6 CRUD Endpoints + Day 7 HTMX UI

Main API application providing CRUD operations and HTMX-powered web interface.

Run with:
    uvicorn notetime.main:app --reload

API will be available at:
    http://localhost:8000/docs (API docs)
    http://localhost:8000 (Web UI)
"""
from datetime import date, timedelta, datetime
from typing import List, Optional
from pathlib import Path
from io import StringIO
import csv
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetime.db import SessionLocal, engine
from notetime.models import Base, Week, Project, Task, WorkEntry, TaskState
from notetime.schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    WorkEntryCreate, WorkEntryUpdate, WorkEntryResponse,
    WeekResponse, WeeklyView,
    ProjectResponse
)
from notetime.summary import generate_weekly_summary
from notetime.nl_parser import parse_entry, EntryType


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


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task.

    Args:
        task_id: ID of task to delete

    Raises:
        404: If task not found
    """
    db_task = db.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    db.delete(db_task)
    db.commit()


# ============================================
# Work Entry Endpoints
# ============================================

@app.post("/api/work_entries", response_model=WorkEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_work_entry_api(
    task_id: int = Form(...),
    date: date = Form(...),
    minutes: Optional[int] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new work entry (time log) - accepts form data for HTMX.

    Args:
        task_id: ID of task
        date: Date of work
        minutes: Minutes worked (optional if start_time/end_time provided)
        start_time: Start time (HH:MM format, optional)
        end_time: End time (HH:MM format, optional)
        note: Optional note

    Returns:
        Created work entry with ID

    Raises:
        404: If task_id doesn't exist
        422: If validation fails (e.g., negative minutes)
    """
    from datetime import datetime
    from notetime.time_engine import duration_minutes

    # Calculate minutes from start/end time if provided
    calculated_minutes = None
    start_time_obj = None
    end_time_obj = None

    if start_time and end_time:
        try:
            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            calculated_minutes = duration_minutes(start_time_obj, end_time_obj)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid time format. Use HH:MM"
            )

    # Use calculated minutes if available, otherwise use provided minutes
    final_minutes = calculated_minutes if calculated_minutes is not None else minutes

    if final_minutes is None or final_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Minutes must be positive or provide valid start/end times"
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
        minutes=final_minutes,
        start_time=start_time_obj,
        end_time=end_time_obj,
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


@app.put("/api/work_entries/{entry_id}", response_model=WorkEntryResponse)
async def update_work_entry(
    entry_id: int,
    entry_update: WorkEntryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a work entry.

    Args:
        entry_id: ID of work entry to update
        entry_update: Fields to update (JSON body)

    Returns:
        Updated work entry

    Raises:
        404: If work entry not found
    """
    from datetime import datetime
    from notetime.time_engine import duration_minutes as calc_duration

    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )

    # Update fields if provided
    if entry_update.date is not None:
        db_entry.date = entry_update.date

    # Handle time updates
    start_time_obj = db_entry.start_time
    end_time_obj = db_entry.end_time

    # Handle explicit start_time update
    if entry_update.start_time is not None:
        if entry_update.start_time == "":
            db_entry.start_time = None
            start_time_obj = None
        else:
            try:
                start_time_obj = datetime.strptime(entry_update.start_time, "%H:%M").time()
                db_entry.start_time = start_time_obj
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid start time format. Use HH:MM"
                )

    # Handle explicit end_time update
    if entry_update.end_time is not None:
        if entry_update.end_time == "":
            db_entry.end_time = None
            end_time_obj = None
        else:
            try:
                end_time_obj = datetime.strptime(entry_update.end_time, "%H:%M").time()
                db_entry.end_time = end_time_obj
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid end time format. Use HH:MM"
                )

    # Handle minutes update
    if entry_update.minutes is not None:
        db_entry.minutes = entry_update.minutes

        # If start_time exists and end_time wasn't explicitly set to null,
        # calculate new end_time based on start_time + minutes
        if start_time_obj and entry_update.end_time is None:
            # Calculate new end time
            start_dt = datetime.combine(datetime.today(), start_time_obj)
            end_dt = start_dt + timedelta(minutes=entry_update.minutes)
            db_entry.end_time = end_dt.time()
            end_time_obj = db_entry.end_time

    # Recalculate minutes if both times are present and minutes wasn't explicitly updated
    if start_time_obj and end_time_obj and entry_update.minutes is None:
        calculated_minutes = calc_duration(start_time_obj, end_time_obj)
        db_entry.minutes = calculated_minutes

    if entry_update.note is not None:
        db_entry.note = entry_update.note

    db.commit()
    db.refresh(db_entry)

    return db_entry


# ============================================
# Natural Language Entry (Notebook Mode)
# ============================================

@app.post("/api/quick-add")
async def quick_add_entry(
    text: str = Form(...),
    week_id: int = Form(...),
    default_task_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Parse and create entry from natural language input.

    Examples:
    - "9-11 worked on API" → time entry
    - "2h fixed bug" → time entry
    - "P1 deploy to production" → task
    - "@API update endpoints" → task with project

    Returns:
        Created entry (task or work entry)
    """
    parsed = parse_entry(text, week_id, default_task_id)

    if parsed["type"] == EntryType.TIME_LOG:
        data = parsed["data"]

        # If no task_id provided, try to find or create a default task
        if not data.get("task_id"):
            # Look for a generic "Misc" task or create one
            misc_task = db.scalar(
                select(Task).where(
                    Task.week_id == week_id,
                    Task.title == "Misc"
                )
            )
            if not misc_task:
                misc_task = Task(
                    title="Misc",
                    week_id=week_id,
                    state="active",
                    priority=3
                )
                db.add(misc_task)
                db.commit()
                db.refresh(misc_task)
            data["task_id"] = misc_task.id

        # Create work entry
        work_entry = WorkEntry(**data)
        db.add(work_entry)
        db.commit()
        db.refresh(work_entry)

        return {
            "type": "time_log",
            "entry": {
                "id": work_entry.id,
                "task_id": work_entry.task_id,
                "date": str(work_entry.date),
                "minutes": work_entry.minutes,
                "note": work_entry.note
            }
        }

    elif parsed["type"] == EntryType.TASK:
        data = parsed["data"]

        # Handle project name if provided
        if "project_name" in data:
            project_name = data.pop("project_name")
            # Find or create project
            project = db.scalar(
                select(Project).where(Project.name == project_name)
            )
            if not project:
                project = Project(name=project_name, is_active=True)
                db.add(project)
                db.commit()
                db.refresh(project)
            data["project_id"] = project.id

        # Create task
        task = Task(**data)
        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "type": "task",
            "entry": {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "state": task.state
            }
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse entry. Try formats like '9-11 worked on API' or 'P1 deploy feature'"
        )


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


@app.get("/api/weeks/{week_id}/export")
def export_week_csv(week_id: int, db: Session = Depends(get_db)):
    """
    Export week data to CSV format.

    Args:
        week_id: ID of week to export

    Returns:
        CSV file with tasks, work entries, and summary

    Raises:
        404: If week not found
    """
    # Get week data
    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {week_id} not found"
        )

    # Get all data
    tasks = db.scalars(select(Task).where(Task.week_id == week_id)).all()

    if tasks:
        task_ids = [task.id for task in tasks]
        work_entries = db.scalars(
            select(WorkEntry).where(WorkEntry.task_id.in_(task_ids))
        ).all()
    else:
        work_entries = []

    # Get projects
    project_ids = list(set(task.project_id for task in tasks if task.project_id is not None))
    projects_map = {}
    if project_ids:
        projects = db.scalars(select(Project).where(Project.id.in_(project_ids))).all()
        projects_map = {p.id: p.name for p in projects}

    # Generate summary
    summary = generate_weekly_summary(week_id, db)

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Week header
    writer.writerow(["Notetime - Weekly Export"])
    writer.writerow(["Week Starting:", week.start_date])
    if week.note:
        writer.writerow(["Note:", week.note])
    writer.writerow([])

    # Tasks section
    writer.writerow(["TASKS"])
    writer.writerow(["Title", "Project", "State", "Priority", "Delegate"])
    for task in tasks:
        project_name = projects_map.get(task.project_id, "")
        writer.writerow([
            task.title,
            project_name,
            task.state,
            task.priority,
            task.delegate or ""
        ])
    writer.writerow([])

    # Work entries section
    writer.writerow(["WORK ENTRIES"])
    writer.writerow(["Task", "Date", "Start Time", "End Time", "Minutes", "Hours", "Note"])
    for entry in work_entries:
        task = next((t for t in tasks if t.id == entry.task_id), None)
        task_title = task.title if task else f"Task {entry.task_id}"
        start_time_str = entry.start_time.strftime("%H:%M") if entry.start_time else ""
        end_time_str = entry.end_time.strftime("%H:%M") if entry.end_time else ""
        writer.writerow([
            task_title,
            entry.date,
            start_time_str,
            end_time_str,
            entry.minutes,
            round(entry.minutes / 60, 2),
            entry.note or ""
        ])
    writer.writerow([])

    # Summary section
    writer.writerow(["WEEKLY SUMMARY"])
    writer.writerow(["Project", "Task", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"])
    for project_name, tasks_data in summary.items():
        for task_name, days in tasks_data.items():
            writer.writerow([
                project_name,
                task_name,
                days.get('Mon', '-'),
                days.get('Tue', '-'),
                days.get('Wed', '-'),
                days.get('Thu', '-'),
                days.get('Fri', '-'),
                days.get('Sat', '-'),
                days.get('Sun', '-'),
                days.get('Total', 0)
            ])

    # Prepare response
    output.seek(0)
    filename = f"notetime_week_{week.start_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================
# Project Endpoints
# ============================================

@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(name: str = Form(None), is_active: bool = Form(True), db: Session = Depends(get_db)):
    """
    Create a new project (form data).

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


@app.post("/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_api(project: dict, db: Session = Depends(get_db)):
    """
    Create a new project (JSON body).

    Args:
        project: JSON with name and is_active fields

    Returns:
        Created project with ID

    Raises:
        400: If project with this name already exists
    """
    name = project.get("name")
    is_active = project.get("is_active", True)

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project name is required"
        )

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


@app.get("/projects/manage", response_class=HTMLResponse)
async def projects_management(request: Request, db: Session = Depends(get_db)):
    """Serve projects management page"""
    # Get all projects (both active and inactive)
    all_projects = db.scalars(select(Project).order_by(Project.is_active.desc(), Project.name)).all()

    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": all_projects
    })


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


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, is_active: bool, db: Session = Depends(get_db)):
    """
    Update a project's status.

    Args:
        project_id: ID of project to update
        is_active: New active status

    Returns:
        Updated project

    Raises:
        404: If project not found
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    project.is_active = is_active
    db.commit()
    db.refresh(project)

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

    # Create chronological timeline (mix tasks and work entries)
    timeline = []

    # Add tasks with creation assumption (use today for active, completion date for done)
    for task in weekly_data.tasks:
        timeline.append({
            "type": "task",
            "date": today,  # Tasks show on today by default
            "time": None,
            "data": task
        })

    # Add work entries
    for entry in weekly_data.work_entries:
        timeline.append({
            "type": "log",
            "date": entry.date,
            "time": entry.start_time,
            "data": entry
        })

    # Sort by date, then time
    timeline.sort(key=lambda x: (
        x["date"],
        x["time"] if x["time"] else datetime.min.time()
    ))

    return templates.TemplateResponse("weekly.html", {
        "request": request,
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary,
        "timeline": timeline
    })


@app.get("/weeks/{week_id}/page", response_class=HTMLResponse)
async def weekly_view_by_id(request: Request, week_id: int, db: Session = Depends(get_db)):
    """Serve weekly page for a specific week"""
    weekly_data = get_week(week_id, db)

    # Create chronological timeline (mix tasks and work entries)
    timeline = []
    today = date.today()

    # Add tasks
    for task in weekly_data.tasks:
        timeline.append({
            "type": "task",
            "date": today,
            "time": None,
            "data": task
        })

    # Add work entries
    for entry in weekly_data.work_entries:
        timeline.append({
            "type": "log",
            "date": entry.date,
            "time": entry.start_time,
            "data": entry
        })

    # Sort by date, then time
    timeline.sort(key=lambda x: (
        x["date"],
        x["time"] if x["time"] else datetime.min.time()
    ))

    return templates.TemplateResponse("weekly.html", {
        "request": request,
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary,
        "timeline": timeline
    })


# ============================================
# HTMX Partial Routes
# ============================================

@app.get("/partials/task-form", response_class=HTMLResponse)
async def task_form_partial(request: Request, week_id: int, db: Session = Depends(get_db)):
    """Return task creation form (HTMX partial)"""
    import json
    projects = db.scalars(select(Project).where(Project.is_active == True)).all()
    projects_json = json.dumps([{"id": p.id, "name": p.name} for p in projects])

    html = f"""
    <form hx-post="/api/tasks" hx-target="#add-task-container" id="task-form">
        <input type="hidden" name="week_id" value="{week_id}">
        <input type="text" name="title" placeholder="Task title" required>

        <div class="project-input-container">
            <input
                type="text"
                id="project-search"
                placeholder="Type to search or create project..."
                autocomplete="off">
            <input type="hidden" name="project_id" id="project-id-field" value="">
            <div id="project-dropdown" class="project-dropdown hidden"></div>
        </div>

        <select name="priority">
            <option value="1">Priority 1 (High)</option>
            <option value="2">Priority 2</option>
            <option value="3" selected>Priority 3 (Normal)</option>
        </select>
        <button type="submit">Add Task</button>
        <button type="button" hx-get="/partials/task-form-cancel" hx-target="#add-task-container">Cancel</button>
    </form>

    <!-- Project creation dialog -->
    <div id="project-create-dialog" class="dialog-hidden">
        <div class="dialog-overlay"></div>
        <div class="dialog-content">
            <h3>Create New Project?</h3>
            <p>Project "<span id="new-project-name"></span>" doesn't exist.</p>
            <p><kbd>Enter</kbd> to create &nbsp;|&nbsp; <kbd>Tab</kbd> to edit name &nbsp;|&nbsp; <kbd>Esc</kbd> to cancel</p>
            <input type="text" id="edit-project-name" class="edit-name-hidden">
            <div class="dialog-actions">
                <button id="confirm-create-project" class="btn-primary">Create Project</button>
                <button id="cancel-create-project">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        const projects = {projects_json};
        const projectSearch = document.getElementById('project-search');
        const projectIdField = document.getElementById('project-id-field');
        const dropdown = document.getElementById('project-dropdown');
        const dialog = document.getElementById('project-create-dialog');
        const newProjectNameSpan = document.getElementById('new-project-name');
        const editProjectNameInput = document.getElementById('edit-project-name');
        const confirmBtn = document.getElementById('confirm-create-project');
        const cancelBtn = document.getElementById('cancel-create-project');

        let pendingProjectName = '';
        let editMode = false;
        let filteredProjects = [];
        let selectedIndex = -1;

        // Show all projects on focus
        projectSearch.addEventListener('focus', function() {{
            showDropdown('');
        }});

        // Filter projects on input
        projectSearch.addEventListener('input', function() {{
            const value = this.value.trim();
            showDropdown(value);

            // Update hidden field if exact match
            const match = projects.find(p => p.name.toLowerCase() === value.toLowerCase());
            projectIdField.value = match ? match.id : '';
        }});

        // Handle keyboard navigation
        projectSearch.addEventListener('keydown', function(e) {{
            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, filteredProjects.length - 1);
                highlightItem();
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                highlightItem();
            }} else if (e.key === 'Tab') {{
                // Auto-complete to first match
                if (filteredProjects.length > 0 && selectedIndex === -1) {{
                    e.preventDefault();
                    selectProject(filteredProjects[0]);
                }} else if (selectedIndex >= 0) {{
                    e.preventDefault();
                    selectProject(filteredProjects[selectedIndex]);
                }}
            }} else if (e.key === 'Enter') {{
                e.preventDefault();

                if (selectedIndex >= 0) {{
                    // Select highlighted item
                    selectProject(filteredProjects[selectedIndex]);
                }} else {{
                    const value = this.value.trim();
                    if (!value) return;

                    // Check if exact match exists
                    const match = projects.find(p => p.name.toLowerCase() === value.toLowerCase());

                    if (!match) {{
                        // Show create dialog
                        hideDropdown();
                        pendingProjectName = value;
                        newProjectNameSpan.textContent = value;
                        dialog.classList.remove('dialog-hidden');
                        editMode = false;
                        editProjectNameInput.classList.add('edit-name-hidden');
                        newProjectNameSpan.style.display = 'inline';
                        confirmBtn.focus();
                    }}
                }}
            }} else if (e.key === 'Escape') {{
                hideDropdown();
            }}
        }});

        // Hide dropdown when clicking outside
        document.addEventListener('click', function(e) {{
            if (!projectSearch.contains(e.target) && !dropdown.contains(e.target)) {{
                hideDropdown();
            }}
        }});

        function showDropdown(filter) {{
            filter = filter.toLowerCase();

            // Filter projects
            filteredProjects = filter
                ? projects.filter(p => p.name.toLowerCase().includes(filter))
                : [...projects];

            selectedIndex = -1;

            if (filteredProjects.length === 0) {{
                dropdown.innerHTML = '<div class="dropdown-item empty">No matching projects</div>';
            }} else {{
                dropdown.innerHTML = filteredProjects.map((p, i) =>
                    `<div class="dropdown-item" data-index="${{i}}">${{p.name}}</div>`
                ).join('');

                // Add click handlers
                dropdown.querySelectorAll('.dropdown-item').forEach(item => {{
                    item.addEventListener('click', function() {{
                        const index = parseInt(this.dataset.index);
                        selectProject(filteredProjects[index]);
                    }});
                }});
            }}

            dropdown.classList.remove('hidden');
        }}

        function hideDropdown() {{
            dropdown.classList.add('hidden');
            selectedIndex = -1;
        }}

        function highlightItem() {{
            dropdown.querySelectorAll('.dropdown-item').forEach((item, i) => {{
                item.classList.toggle('highlighted', i === selectedIndex);
            }});
        }}

        function selectProject(project) {{
            projectSearch.value = project.name;
            projectIdField.value = project.id;
            hideDropdown();
            document.querySelector('[name="priority"]').focus();
        }}

        // Dialog keyboard navigation (unchanged)
        dialog.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                e.preventDefault();
                closeDialog();
            }} else if (e.key === 'Enter' && !editMode) {{
                e.preventDefault();
                createProject();
            }} else if (e.key === 'Tab' && !editMode && e.target === confirmBtn) {{
                e.preventDefault();
                editMode = true;
                editProjectNameInput.value = pendingProjectName;
                editProjectNameInput.classList.remove('edit-name-hidden');
                newProjectNameSpan.style.display = 'none';
                editProjectNameInput.focus();
                editProjectNameInput.select();
            }}
        }});

        editProjectNameInput.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                e.preventDefault();
                pendingProjectName = this.value.trim();
                createProject();
            }} else if (e.key === 'Tab') {{
                e.preventDefault();
                closeDialog();
            }}
        }});

        confirmBtn.addEventListener('click', createProject);
        cancelBtn.addEventListener('click', closeDialog);

        async function createProject() {{
            if (!pendingProjectName) return;

            try {{
                const response = await fetch('/api/projects', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        name: pendingProjectName,
                        is_active: true
                    }})
                }});

                if (response.ok) {{
                    const newProject = await response.json();
                    projects.push(newProject);
                    projectSearch.value = newProject.name;
                    projectIdField.value = newProject.id;
                    closeDialog();
                    document.querySelector('[name="priority"]').focus();
                }}
            }} catch (error) {{
                console.error('Error creating project:', error);
                alert('Failed to create project');
            }}
        }}

        function closeDialog() {{
            dialog.classList.add('dialog-hidden');
            editMode = false;
            editProjectNameInput.classList.add('edit-name-hidden');
            newProjectNameSpan.style.display = 'inline';
            projectSearch.focus();
        }}
    </script>
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
    <form hx-post="/api/work_entries" hx-target="#add-log-container" id="log-time-form">
        <select name="task_id" required>
            <option value="">Select task...</option>
            {"".join(f'<option value="{t.id}">{t.title}</option>' for t in tasks)}
        </select>
        <input type="date" name="date" value="{date.today()}" required>

        <div class="time-entry-group">
            <label>Option 1: Enter time range (e.g., type "9" for 09:00)</label>
            <div class="time-inputs">
                <input type="text"
                       id="start_time_display"
                       placeholder="Start (e.g., 9 or 9:30)"
                       autocomplete="off">
                <input type="hidden" name="start_time" id="start_time">
                <span>to</span>
                <input type="text"
                       id="end_time_display"
                       placeholder="End (e.g., 17 or 17:30)"
                       autocomplete="off">
                <input type="hidden" name="end_time" id="end_time">
            </div>
        </div>

        <div class="time-entry-group">
            <label>Option 2: Enter duration directly</label>
            <input type="number" name="minutes" id="minutes" placeholder="Minutes worked" min="1">
        </div>

        <textarea name="note" placeholder="Note (optional)" rows="2"></textarea>
        <button type="submit">Log Time</button>
        <button type="button" hx-get="/partials/log-form-cancel" hx-target="#add-log-container">Cancel</button>
    </form>
    <script>
        const startDisplay = document.getElementById('start_time_display');
        const endDisplay = document.getElementById('end_time_display');
        const startHidden = document.getElementById('start_time');
        const endHidden = document.getElementById('end_time');
        const minutesInput = document.getElementById('minutes');

        // Smart time formatting function
        function formatTimeInput(input) {{
            let value = input.value.trim();
            if (!value) return '';

            // Remove any non-digit/colon characters
            value = value.replace(/[^0-9:]/g, '');

            // If just a number (no colon)
            if (!value.includes(':')) {{
                // Handle formats like 930 (9:30), 1430 (14:30), or just 9 (9:00)
                if (value.length === 3 || value.length === 4) {{
                    // Parse as HHMM or HMM
                    let hour, minute;
                    if (value.length === 3) {{
                        // HMM format (e.g., 930 = 9:30)
                        hour = parseInt(value.substring(0, 1));
                        minute = parseInt(value.substring(1, 3));
                    }} else {{
                        // HHMM format (e.g., 1430 = 14:30)
                        hour = parseInt(value.substring(0, 2));
                        minute = parseInt(value.substring(2, 4));
                    }}

                    if (hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59) {{
                        return hour.toString().padStart(2, '0') + ':' + minute.toString().padStart(2, '0');
                    }}
                }}

                // Single or double digit hour only
                let hour = parseInt(value);
                if (isNaN(hour)) return '';

                // Default to :00 minutes
                if (hour >= 0 && hour <= 23) {{
                    return hour.toString().padStart(2, '0') + ':00';
                }}
                return '';
            }}

            // If has colon, parse hour:minute
            const parts = value.split(':');
            let hour = parseInt(parts[0]);
            let minute = parseInt(parts[1]) || 0;

            if (isNaN(hour) || hour < 0 || hour > 23) return '';
            if (isNaN(minute) || minute < 0 || minute > 59) minute = 0;

            return hour.toString().padStart(2, '0') + ':' + minute.toString().padStart(2, '0');
        }}

        // Handle blur events to format time
        startDisplay.addEventListener('blur', function() {{
            const formatted = formatTimeInput(this);
            if (formatted) {{
                this.value = formatted;
                startHidden.value = formatted;
                calculateDuration();
            }}
        }});

        endDisplay.addEventListener('blur', function() {{
            const formatted = formatTimeInput(this);
            if (formatted) {{
                this.value = formatted;
                endHidden.value = formatted;
                calculateDuration();
            }}
        }});

        // Handle Enter key for quick formatting
        startDisplay.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' || e.key === 'Tab') {{
                const formatted = formatTimeInput(this);
                if (formatted) {{
                    this.value = formatted;
                    startHidden.value = formatted;
                    calculateDuration();
                }}
            }}
        }});

        endDisplay.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' || e.key === 'Tab') {{
                const formatted = formatTimeInput(this);
                if (formatted) {{
                    this.value = formatted;
                    endHidden.value = formatted;
                    calculateDuration();
                }}
            }}
        }});

        function calculateDuration() {{
            if (startHidden.value && endHidden.value) {{
                const start = startHidden.value.split(':');
                const end = endHidden.value.split(':');
                const startMins = parseInt(start[0]) * 60 + parseInt(start[1]);
                const endMins = parseInt(end[0]) * 60 + parseInt(end[1]);
                const duration = endMins - startMins;

                if (duration > 0) {{
                    minutesInput.value = duration;
                    minutesInput.readOnly = true;
                }} else {{
                    minutesInput.readOnly = false;
                }}
            }} else {{
                minutesInput.readOnly = false;
            }}
        }}

        minutesInput.addEventListener('input', function() {{
            if (this.value) {{
                startDisplay.value = '';
                endDisplay.value = '';
                startHidden.value = '';
                endHidden.value = '';
            }}
        }});
    </script>
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
    """Set task state to 'waiting' (HTMX action)"""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.state = TaskState.WAITING.value
    db.commit()

    # Return updated task HTML
    return HTMLResponse(content=f'<div class="task-item task-waiting">⏸ {task.title} (Waiting)</div>')


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
