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
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from notetime.db import SessionLocal, engine, get_db
from notetime.models import Base, Week, Project, Task, WorkEntry, TaskState, User, Feedback
from notetime.schemas import (
    TaskCreate, TaskResponse, TaskUpdate,
    WorkEntryCreate, WorkEntryResponse, WorkEntryUpdate,
    WeekCreate, WeekResponse, WeeklyView,
    ProjectCreate, ProjectResponse, ProjectUpdate,
    UserRegister, UserLogin, Token, UserResponse,
    FeedbackCreate, FeedbackResponse
)
from notetime.summary import generate_weekly_summary
from notetime.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_optional_current_user
)


# Create database tables (commented out for testing - tables should be created via migrations or seed scripts)
# Base.metadata.create_all(bind=engine)


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


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user_data: User registration data (email, username, password)

    Returns:
        Created user details (without password)

    Raises:
        400: If username or email already exists
    """
    # Check if username already exists
    existing_user = db.scalars(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = db.scalars(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login and get access token.

    Args:
        form_data: OAuth2 form with username (or email) and password

    Returns:
        Access token

    Raises:
        401: If credentials are invalid
    """
    # Find user by username or email
    user = db.scalars(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token, token_type="bearer")


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user details.

    Returns:
        Current user details

    Requires:
        Valid authentication token
    """
    return current_user


# ============================================
# Authentication UI Routes
# ============================================

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse(request, "login.html")


@app.post("/auth/login", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    # Find user by username
    user = db.scalars(
        select(User).where(User.username == username)
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Incorrect username or password"},
            status_code=401
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Account is inactive"},
            status_code=400
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Redirect to home page with token in cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7 days
        samesite="lax"
    )
    return response


@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page"""
    return templates.TemplateResponse(request, "register.html")


@app.post("/auth/register", response_class=HTMLResponse)
async def register_form(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle registration form submission"""
    # Validate username length
    if len(username) < 3:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Username must be at least 3 characters"},
            status_code=400
        )

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Password must be at least 6 characters"},
            status_code=400
        )

    # Check if username already exists
    existing_user = db.scalars(
        select(User).where(User.username == username)
    ).first()
    if existing_user:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Username already registered"},
            status_code=400
        )

    # Check if email already exists
    existing_email = db.scalars(
        select(User).where(User.email == email)
    ).first()
    if existing_email:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Email already registered"},
            status_code=400
        )

    # Create new user
    hashed_password = get_password_hash(password)
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})

    # Redirect to home page with token in cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7 days
        samesite="lax"
    )
    return response


@app.get("/auth/logout")
async def logout():
    """Logout and clear authentication cookie"""
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# ============================================
# Week API Endpoints
# ============================================

@app.post("/api/weeks", response_model=WeekResponse)
async def create_week_api(
    week_data: WeekCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new week (API endpoint with JSON body).

    Args:
        week_data: Week creation data (start_date, note)

    Returns:
        Created week with ID

    Raises:
        400: If week with this start_date already exists for this user
    """
    # Check if week already exists for this user
    existing = db.scalars(
        select(Week).where(
            Week.start_date == week_data.start_date,
            Week.user_id == current_user.id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week starting {week_data.start_date} already exists"
        )

    # Create week
    db_week = Week(
        start_date=week_data.start_date,
        note=week_data.note,
        user_id=current_user.id
    )
    db.add(db_week)
    db.commit()
    db.refresh(db_week)

    return db_week


@app.get("/api/weeks", response_model=List[WeekResponse])
async def list_weeks_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all weeks for the authenticated user (API endpoint).

    Returns:
        List of weeks belonging to the user
    """
    weeks = db.scalars(
        select(Week).where(Week.user_id == current_user.id).order_by(Week.start_date.desc())
    ).all()
    return weeks


@app.get("/api/weeks/{week_id}", response_model=WeekResponse)
async def get_week_api(
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific week by ID."""
    week = db.get(Week, week_id)
    if not week or week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {week_id} not found"
        )
    return week


@app.get("/api/weeks/{week_id}/tasks", response_model=List[TaskResponse])
async def list_tasks_for_week_api(
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all tasks for a specific week."""
    week = db.get(Week, week_id)
    if not week or week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {week_id} not found"
        )
    tasks = db.scalars(select(Task).where(Task.week_id == week_id)).all()
    return tasks


# ============================================
# Project API Endpoints
# ============================================

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project_api(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project (API endpoint with JSON body).

    Args:
        project_data: Project creation data (name, is_active)

    Returns:
        Created project with ID

    Raises:
        400: If project with this name already exists for this user
    """
    # Check if project already exists for this user
    existing = db.scalars(
        select(Project).where(
            Project.name == project_data.name,
            Project.user_id == current_user.id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project '{project_data.name}' already exists"
        )

    # Create project
    db_project = Project(
        name=project_data.name,
        is_active=project_data.is_active,
        user_id=current_user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects_api(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all projects for the authenticated user (API endpoint).

    Args:
        active_only: If True, only return active projects (default: True)

    Returns:
        List of projects belonging to the user
    """
    query = select(Project).where(Project.user_id == current_user.id)
    if active_only:
        query = query.where(Project.is_active == True)

    projects = db.scalars(query).all()
    return projects


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project_api(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project by ID."""
    project = db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project_api(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing project."""
    project = db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.is_active is not None:
        project.is_active = project_data.is_active
    db.commit()
    db.refresh(project)
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project_api(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project."""
    project = db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ============================================
# Task Endpoints
# ============================================

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task_api(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task (JSON body).

    Args:
        task_data: Task creation data (title, week_id, state, priority, project_id, delegate)

    Returns:
        Created task with ID

    Raises:
        404: If week_id or project_id doesn't exist or doesn't belong to user
    """
    # Verify week exists and belongs to user
    week = db.get(Week, task_data.week_id)
    if not week or week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Week with id {task_data.week_id} not found"
        )

    # Verify project exists and belongs to user if provided
    if task_data.project_id is not None:
        project = db.get(Project, task_data.project_id)
        if not project or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {task_data.project_id} not found"
            )

    # Create task
    db_task = Task(
        title=task_data.title,
        week_id=task_data.week_id,
        state=task_data.state,
        priority=task_data.priority,
        project_id=task_data.project_id,
        delegate=task_data.delegate
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task_api(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing task (JSON body)."""
    db_task = db.get(Task, task_id)
    if not db_task or db_task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    if task_data.title is not None:
        db_task.title = task_data.title
    if task_data.state is not None:
        valid_states = [s.value for s in TaskState]
        if task_data.state not in valid_states:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid state. Must be one of: {valid_states}"
            )
        db_task.state = task_data.state
    if task_data.priority is not None:
        db_task.priority = task_data.priority
    if task_data.delegate is not None:
        db_task.delegate = task_data.delegate

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing task (query params, legacy endpoint)."""
    db_task = db.get(Task, task_id)
    if not db_task or db_task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    if title is not None:
        db_task.title = title
    if state is not None:
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
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific task by ID.

    Args:
        task_id: ID of task to retrieve

    Returns:
        Task details

    Raises:
        404: If task not found or doesn't belong to user
    """
    db_task = db.get(Task, task_id)
    if not db_task or db_task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )

    return db_task


# ============================================
# Work Entry Endpoints
# ============================================

@app.post("/api/work_entries", response_model=WorkEntryResponse)
async def create_work_entry_api(
    entry_data: WorkEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new work entry (time log) - JSON body.

    Args:
        entry_data: Work entry creation data (task_id, date, minutes, note)

    Returns:
        Created work entry with ID

    Raises:
        404: If task_id doesn't exist or doesn't belong to user
        422: If validation fails (e.g., negative minutes)
    """
    # Verify task exists and belongs to user
    task = db.get(Task, entry_data.task_id)
    if not task or task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {entry_data.task_id} not found"
        )

    # Create work entry
    db_entry = WorkEntry(
        task_id=entry_data.task_id,
        date=entry_data.date,
        minutes=entry_data.minutes,
        note=entry_data.note
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    return db_entry


@app.get("/api/tasks/{task_id}/work_entries", response_model=List[WorkEntryResponse])
async def list_work_entries_for_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all work entries for a specific task."""
    task = db.get(Task, task_id)
    if not task or task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    entries = db.scalars(select(WorkEntry).where(WorkEntry.task_id == task_id)).all()
    return entries


@app.get("/api/work_entries/{entry_id}", response_model=WorkEntryResponse)
async def get_work_entry_api(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific work entry by ID."""
    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry or db_entry.task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )
    return db_entry


@app.put("/api/work_entries/{entry_id}", response_model=WorkEntryResponse)
async def update_work_entry_api(
    entry_id: int,
    entry_data: WorkEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing work entry."""
    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry or db_entry.task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )
    if entry_data.minutes is not None:
        if entry_data.minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Minutes must be positive"
            )
        db_entry.minutes = entry_data.minutes
    if entry_data.note is not None:
        db_entry.note = entry_data.note
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.delete("/api/work_entries/{entry_id}")
async def delete_work_entry_api(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a work entry."""
    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry or db_entry.task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )
    db.delete(db_entry)
    db.commit()
    return {"message": "Work entry deleted"}


@app.get("/work_entries/{entry_id}", response_model=WorkEntryResponse)
def get_work_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific work entry by ID (legacy endpoint without /api/ prefix)."""
    db_entry = db.get(WorkEntry, entry_id)
    if not db_entry or db_entry.task.week.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work entry with id {entry_id} not found"
        )
    return db_entry


# ============================================
# Week Endpoints
# ============================================

@app.post("/weeks", response_model=WeekResponse, status_code=status.HTTP_201_CREATED)
def create_week(
    start_date: date,
    note: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new week.

    Args:
        start_date: Monday start date for the week
        note: Optional note for the week

    Returns:
        Created week with ID

    Raises:
        400: If week with this start_date already exists for this user
    """
    # Check if week already exists for this user
    existing = db.scalars(
        select(Week).where(
            Week.start_date == start_date,
            Week.user_id == current_user.id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week starting {start_date} already exists"
        )

    # Create week
    db_week = Week(start_date=start_date, note=note, user_id=current_user.id)
    db.add(db_week)
    db.commit()
    db.refresh(db_week)

    return db_week


@app.get("/weeks/current", response_model=WeeklyView)
def get_current_week(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current week's data for the authenticated user.

    Finds or creates the week starting on the most recent Monday.

    Returns:
        WeeklyView for current week
    """
    # Calculate current week's Monday
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    # Find or create week for this user
    week = db.scalars(
        select(Week).where(
            Week.start_date == week_start,
            Week.user_id == current_user.id
        )
    ).first()

    if not week:
        # Create the week if it doesn't exist
        week = Week(start_date=week_start, user_id=current_user.id)
        db.add(week)
        db.commit()
        db.refresh(week)

    # Return full weekly view
    return get_week(week.id, current_user, db)


@app.get("/weeks/{week_id}", response_model=WeeklyView)
def get_week(
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete weekly view including tasks, work entries, and summary.

    Args:
        week_id: ID of week to retrieve

    Returns:
        WeeklyView with week, tasks, work entries, projects, and summary

    Raises:
        404: If week not found or doesn't belong to user
    """
    # Get week and verify ownership
    week = db.get(Week, week_id)
    if not week or week.user_id != current_user.id:
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

    # Get all projects referenced by tasks (only user's projects)
    project_ids = list(set(task.project_id for task in tasks if task.project_id is not None))
    if project_ids:
        projects = db.scalars(
            select(Project).where(
                Project.id.in_(project_ids),
                Project.user_id == current_user.id
            )
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
def create_project(
    name: str,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new project.

    Args:
        name: Project name (must be unique per user)
        is_active: Whether project is active (default: True)

    Returns:
        Created project with ID

    Raises:
        400: If project with this name already exists for this user
    """
    # Check if project already exists for this user
    existing = db.scalars(
        select(Project).where(
            Project.name == name,
            Project.user_id == current_user.id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project '{name}' already exists"
        )

    # Create project
    db_project = Project(name=name, is_active=is_active, user_id=current_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@app.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all projects for the authenticated user.

    Args:
        active_only: If True, only return active projects (default: True)

    Returns:
        List of projects belonging to the user
    """
    query = select(Project).where(Project.user_id == current_user.id)
    if active_only:
        query = query.where(Project.is_active == True)

    projects = db.scalars(query).all()
    return projects


@app.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific project by ID.

    Args:
        project_id: ID of project to retrieve

    Returns:
        Project details

    Raises:
        404: If project not found or doesn't belong to user
    """
    project = db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    return project


# ============================================
# Web UI Routes (HTMX)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def weekly_view(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Serve the weekly HTML page (current week).

    This is the main web interface.
    """
    # Get or create current week for this user
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    week = db.scalars(
        select(Week).where(
            Week.start_date == week_start,
            Week.user_id == current_user.id
        )
    ).first()

    if not week:
        week = Week(start_date=week_start, user_id=current_user.id)
        db.add(week)
        db.commit()
        db.refresh(week)

    # Get weekly data
    weekly_data = get_week(week.id, current_user, db)

    # Get all active projects for the current user (for task creation dropdown)
    all_projects = db.scalars(
        select(Project).where(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).order_by(Project.name)
    ).all()

    return templates.TemplateResponse(request, "weekly.html", {
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary,
        "user": current_user,
        "all_projects": [{"id": p.id, "name": p.name} for p in all_projects]
    })


@app.get("/weeks/{week_id}/page", response_class=HTMLResponse)
async def weekly_view_by_id(
    request: Request,
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve weekly page for a specific week"""
    weekly_data = get_week(week_id, current_user, db)

    # Get all active projects for the current user (for task creation dropdown)
    all_projects = db.scalars(
        select(Project).where(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).order_by(Project.name)
    ).all()

    return templates.TemplateResponse(request, "weekly.html", {
        "week": weekly_data.week,
        "tasks": weekly_data.tasks,
        "work_entries": weekly_data.work_entries,
        "projects": weekly_data.projects,
        "summary": weekly_data.summary,
        "user": current_user,
        "all_projects": [{"id": p.id, "name": p.name} for p in all_projects]
    })


# ============================================
# HTMX Partial Routes
# ============================================

@app.post("/htmx/tasks", response_model=TaskResponse)
async def create_task_htmx(
    title: str = Form(...),
    week_id: int = Form(...),
    state: str = Form("active"),
    priority: int = Form(3),
    project_id: Optional[int] = Form(None),
    delegate: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task from HTMX form (accepts form data)."""
    week = db.get(Week, week_id)
    if not week or week.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Week with id {week_id} not found")

    if project_id is not None:
        project = db.get(Project, project_id)
        if not project or project.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with id {project_id} not found")

    db_task = Task(title=title, week_id=week_id, state=state, priority=priority, project_id=project_id, delegate=delegate)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.post("/htmx/work_entries", response_model=WorkEntryResponse)
async def create_work_entry_htmx(
    task_id: int = Form(...),
    date: date = Form(...),
    minutes: int = Form(...),
    note: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new work entry from HTMX form (accepts form data)."""
    if minutes <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Minutes must be positive")

    task = db.get(Task, task_id)
    if not task or task.week.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found")

    db_entry = WorkEntry(task_id=task_id, date=date, minutes=minutes, note=note)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.get("/partials/task-form", response_class=HTMLResponse)
async def task_form_partial(
    request: Request,
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return task creation form (HTMX partial)"""
    projects = db.scalars(
        select(Project).where(
            Project.is_active == True,
            Project.user_id == current_user.id
        )
    ).all()

    html = f"""
    <form hx-post="/htmx/tasks" hx-target="#add-task-container">
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
async def log_form_partial(
    request: Request,
    week_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return work entry form (HTMX partial)"""
    # Verify week belongs to user
    week = db.get(Week, week_id)
    if not week or week.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Week not found")

    tasks = db.scalars(select(Task).where(Task.week_id == week_id)).all()

    html = f"""
    <form hx-post="/htmx/work_entries" hx-target="#add-log-container">
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
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark task as completed (HTMX action)"""
    task = db.get(Task, task_id)
    if not task or task.week.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    task.state = TaskState.COMPLETED.value
    db.commit()

    # Return updated task HTML
    return HTMLResponse(content=f'<div class="task-item task-completed">✓ {task.title} (Completed)</div>')


@app.put("/api/tasks/{task_id}/defer", response_class=HTMLResponse)
async def defer_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark task for deferral (HTMX action)"""
    # In a full implementation, this would rollover to next week
    # For now, just mark it visually
    task = db.get(Task, task_id)
    if not task or task.week.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    return HTMLResponse(content=f'<div class="task-item">→ {task.title} (Will be moved to next week)</div>')


# ============================================
# Feedback
# ============================================

VALID_CATEGORIES = {"bug_report", "feature_request", "general", "ui_ux", "performance"}
VALID_SEVERITIES = {"critical", "high", "medium", "low", ""}
VALID_REPRODUCIBILITY = {"always", "sometimes", "rarely", "na", ""}


@app.get("/feedback", response_class=HTMLResponse)
async def feedback_form(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Render the beta feedback form."""
    return templates.TemplateResponse(
        request, "feedback.html",
        {"current_user": current_user, "success": False, "error": None},
    )


@app.post("/feedback", response_class=HTMLResponse)
async def submit_feedback_form(
    request: Request,
    category: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    rating: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    browser_info: Optional[str] = Form(None),
    reproducibility: Optional[str] = Form(None),
    severity: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Handle beta feedback form submission."""
    # Validate
    if category not in VALID_CATEGORIES:
        return templates.TemplateResponse(
            request, "feedback.html",
            {"current_user": current_user, "success": False,
             "error": "Please select a valid feedback category."},
            status_code=422,
        )
    title = title.strip()
    description = description.strip()
    if not title or len(title) > 200:
        return templates.TemplateResponse(
            request, "feedback.html",
            {"current_user": current_user, "success": False,
             "error": "Title is required and must be 200 characters or fewer."},
            status_code=422,
        )
    if not description:
        return templates.TemplateResponse(
            request, "feedback.html",
            {"current_user": current_user, "success": False,
             "error": "Description is required."},
            status_code=422,
        )

    # Parse optional fields
    rating_int: Optional[int] = None
    if rating:
        try:
            rating_int = int(rating)
            if not (1 <= rating_int <= 5):
                rating_int = None
        except ValueError:
            rating_int = None

    severity_val = severity if severity in VALID_SEVERITIES - {""} else None
    repro_val = reproducibility if reproducibility in VALID_REPRODUCIBILITY - {""} else None
    contact = contact_email.strip() if contact_email and contact_email.strip() else None
    browser = browser_info.strip() if browser_info and browser_info.strip() else None

    feedback = Feedback(
        user_id=current_user.id if current_user else None,
        category=category,
        title=title,
        description=description,
        rating=rating_int,
        contact_email=contact,
        browser_info=browser,
        reproducibility=repro_val,
        severity=severity_val,
    )
    db.add(feedback)
    db.commit()

    return templates.TemplateResponse(
        request, "feedback.html",
        {"current_user": current_user, "success": True, "error": None},
    )


@app.post("/api/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback_api(
    payload: FeedbackCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Submit feedback via JSON API."""
    feedback = Feedback(
        user_id=current_user.id if current_user else None,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        rating=payload.rating,
        contact_email=payload.contact_email,
        browser_info=payload.browser_info,
        reproducibility=payload.reproducibility,
        severity=payload.severity,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@app.get("/api/feedback", response_model=List[FeedbackResponse])
async def list_feedback(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List feedback submitted by the current user."""
    entries = db.execute(
        select(Feedback).where(Feedback.user_id == current_user.id).order_by(Feedback.submitted_at.desc())
    ).scalars().all()
    return entries


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
