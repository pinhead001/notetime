"""
Integration tests for main API endpoints (weeks, tasks, projects, work entries)

Run with: pytest tests/test_api_main.py -v
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from notetime.main import app
from notetime.models import Base
from notetime.db import get_db


@pytest.fixture
def test_db():
    """Create in-memory test database"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield SessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """Create authenticated test client"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePassword123"
        }
    )

    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "test@example.com",
            "password": "SecurePassword123"
        }
    )
    token = login_response.json()["access_token"]

    # Add authorization header to client
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestWeekAPI:
    """Test week API endpoints"""

    def test_create_week(self, auth_client):
        """Test creating a new week"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["start_date"] == week_start.isoformat()

    def test_list_weeks(self, auth_client):
        """Test listing weeks"""
        # Create a week first
        week_start = date.today() - timedelta(days=date.today().weekday())
        auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )

        # List weeks
        response = auth_client.get("/api/weeks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_week(self, auth_client):
        """Test getting a specific week"""
        # Create a week
        week_start = date.today() - timedelta(days=date.today().weekday())
        create_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = create_response.json()["id"]

        # Get the week
        response = auth_client.get(f"/api/weeks/{week_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == week_id
        assert data["start_date"] == week_start.isoformat()

    def test_week_isolation_between_users(self, client, auth_client):
        """Test that users can only see their own weeks"""
        # Create week with first user
        week_start = date.today() - timedelta(days=date.today().weekday())
        create_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = create_response.json()["id"]

        # Create second user
        client.post(
            "/api/auth/register",
            json={
                "email": "test2@example.com",
                "username": "testuser2",
                "password": "SecurePassword456"
            }
        )
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "test2@example.com",
                "password": "SecurePassword456"
            }
        )
        token2 = login_response.json()["access_token"]

        # Try to access first user's week with second user's token
        response = client.get(
            f"/api/weeks/{week_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        # Should return 404 or 403
        assert response.status_code in [404, 403]


class TestProjectAPI:
    """Test project API endpoints"""

    def test_create_project(self, auth_client):
        """Test creating a new project"""
        response = auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Project"
        assert data["is_active"] is True

    def test_list_projects(self, auth_client):
        """Test listing projects"""
        # Create a project first
        auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )

        # List projects
        response = auth_client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_project(self, auth_client):
        """Test updating a project"""
        # Create a project
        create_response = auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        project_id = create_response.json()["id"]

        # Update the project
        response = auth_client.put(
            f"/api/projects/{project_id}",
            json={"name": "Updated Project", "is_active": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project"
        assert data["is_active"] is False

    def test_delete_project(self, auth_client):
        """Test deleting a project"""
        # Create a project
        create_response = auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        project_id = create_response.json()["id"]

        # Delete the project
        response = auth_client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200

        # Verify it's deleted
        response = auth_client.get(f"/api/projects/{project_id}")
        assert response.status_code == 404


class TestTaskAPI:
    """Test task API endpoints"""

    def test_create_task(self, auth_client):
        """Test creating a new task"""
        # Create a week first
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        # Create a task
        response = auth_client.post(
            "/api/tasks",
            json={
                "title": "Test Task",
                "week_id": week_id,
                "priority": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Task"
        assert data["week_id"] == week_id
        assert data["priority"] == 1
        assert data["state"] == "active"

    def test_list_tasks_for_week(self, auth_client):
        """Test listing tasks for a specific week"""
        # Create a week
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        # Create tasks
        auth_client.post(
            "/api/tasks",
            json={"title": "Task 1", "week_id": week_id}
        )
        auth_client.post(
            "/api/tasks",
            json={"title": "Task 2", "week_id": week_id}
        )

        # List tasks for the week
        response = auth_client.get(f"/api/weeks/{week_id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_update_task_state(self, auth_client):
        """Test updating task state"""
        # Create week and task
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        task_response = auth_client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": week_id}
        )
        task_id = task_response.json()["id"]

        # Update task state
        response = auth_client.put(
            f"/api/tasks/{task_id}",
            json={"state": "completed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"

    def test_create_task_with_project(self, auth_client):
        """Test creating a task with project association"""
        # Create week and project
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        project_response = auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        project_id = project_response.json()["id"]

        # Create task with project
        response = auth_client.post(
            "/api/tasks",
            json={
                "title": "Project Task",
                "week_id": week_id,
                "project_id": project_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id


class TestWorkEntryAPI:
    """Test work entry API endpoints"""

    def test_create_work_entry(self, auth_client):
        """Test creating a work entry"""
        # Create week and task
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        task_response = auth_client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": week_id}
        )
        task_id = task_response.json()["id"]

        # Create work entry
        today = date.today()
        response = auth_client.post(
            "/api/work_entries",
            json={
                "task_id": task_id,
                "date": today.isoformat(),
                "minutes": 120,
                "note": "Worked on feature"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["task_id"] == task_id
        assert data["minutes"] == 120
        assert data["note"] == "Worked on feature"

    def test_list_work_entries_for_task(self, auth_client):
        """Test listing work entries for a task"""
        # Create week and task
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        task_response = auth_client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": week_id}
        )
        task_id = task_response.json()["id"]

        # Create work entries
        today = date.today()
        auth_client.post(
            "/api/work_entries",
            json={
                "task_id": task_id,
                "date": today.isoformat(),
                "minutes": 60
            }
        )
        auth_client.post(
            "/api/work_entries",
            json={
                "task_id": task_id,
                "date": today.isoformat(),
                "minutes": 90
            }
        )

        # List work entries
        response = auth_client.get(f"/api/tasks/{task_id}/work_entries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_update_work_entry(self, auth_client):
        """Test updating a work entry"""
        # Create week, task, and work entry
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        task_response = auth_client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": week_id}
        )
        task_id = task_response.json()["id"]

        today = date.today()
        entry_response = auth_client.post(
            "/api/work_entries",
            json={
                "task_id": task_id,
                "date": today.isoformat(),
                "minutes": 60
            }
        )
        entry_id = entry_response.json()["id"]

        # Update work entry
        response = auth_client.put(
            f"/api/work_entries/{entry_id}",
            json={"minutes": 120, "note": "Updated note"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["minutes"] == 120
        assert data["note"] == "Updated note"

    def test_delete_work_entry(self, auth_client):
        """Test deleting a work entry"""
        # Create week, task, and work entry
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_response = auth_client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        week_id = week_response.json()["id"]

        task_response = auth_client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": week_id}
        )
        task_id = task_response.json()["id"]

        today = date.today()
        entry_response = auth_client.post(
            "/api/work_entries",
            json={
                "task_id": task_id,
                "date": today.isoformat(),
                "minutes": 60
            }
        )
        entry_id = entry_response.json()["id"]

        # Delete work entry
        response = auth_client.delete(f"/api/work_entries/{entry_id}")
        assert response.status_code == 200

        # Verify deletion
        response = auth_client.get(f"/api/work_entries/{entry_id}")
        assert response.status_code == 404


class TestUnauthorizedAccess:
    """Test that API endpoints require authentication"""

    def test_create_week_unauthorized(self, client):
        """Test creating week without authentication"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        response = client.post(
            "/api/weeks",
            json={"start_date": week_start.isoformat()}
        )
        assert response.status_code == 401

    def test_list_weeks_unauthorized(self, client):
        """Test listing weeks without authentication"""
        response = client.get("/api/weeks")
        assert response.status_code == 401

    def test_create_project_unauthorized(self, client):
        """Test creating project without authentication"""
        response = client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        assert response.status_code == 401

    def test_create_task_unauthorized(self, client):
        """Test creating task without authentication"""
        response = client.post(
            "/api/tasks",
            json={"title": "Test Task", "week_id": 1}
        )
        assert response.status_code == 401
