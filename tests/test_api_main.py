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
    # Use StaticPool to ensure all connections share the same in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=__import__('sqlalchemy.pool', fromlist=['StaticPool']).StaticPool
    )
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
        """Test soft-deleting a project (sets is_active=False)"""
        # Create a project
        create_response = auth_client.post(
            "/api/projects",
            json={"name": "Test Project"}
        )
        project_id = create_response.json()["id"]

        # Soft-delete the project
        response = auth_client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200

        # Project still exists (soft-deleted), GET should still return it
        get_response = auth_client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False

        # Should not appear in the default active-only project list
        list_response = auth_client.get("/api/projects")
        project_ids = [p["id"] for p in list_response.json()]
        assert project_id not in project_ids


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


class TestNewTaskEndpoints:
    """Tests for delete, uncomplete, move-up, move-down, and list-all-tasks"""

    def _setup_week_and_tasks(self, auth_client, num_tasks=2):
        """Helper: create a week and num_tasks tasks; return (week_id, [task_id, ...])"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]
        task_ids = []
        for i in range(num_tasks):
            resp = auth_client.post(
                "/api/tasks",
                json={"title": f"Task {i + 1}", "week_id": week_id}
            )
            task_ids.append(resp.json()["id"])
        return week_id, task_ids

    def test_delete_task(self, auth_client):
        """DELETE /api/tasks/{id} removes the task"""
        _, (task_id,) = self._setup_week_and_tasks(auth_client, num_tasks=1)
        response = auth_client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Task deleted"

        # Subsequent GET should 404
        get_resp = auth_client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == 404

    def test_uncomplete_task(self, auth_client):
        """PUT /api/tasks/{id}/uncomplete restores a completed task to active"""
        _, (task_id,) = self._setup_week_and_tasks(auth_client, num_tasks=1)

        # First complete it
        auth_client.put(f"/api/tasks/{task_id}", json={"state": "completed"})

        # Then uncomplete
        response = auth_client.put(f"/api/tasks/{task_id}/uncomplete")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "active"

        # Verify via GET
        get_resp = auth_client.get(f"/api/tasks/{task_id}")
        assert get_resp.json()["state"] == "active"

    def test_move_task_up(self, auth_client):
        """POST /api/tasks/{id}/move-up swaps sort_order with the task above"""
        _, (task1_id, task2_id) = self._setup_week_and_tasks(auth_client, num_tasks=2)

        # task1 is at index 0, task2 at index 1; move task2 up
        response = auth_client.post(f"/api/tasks/{task2_id}/move-up")
        assert response.status_code == 200
        assert response.json()["message"] == "Moved up"

    def test_move_task_up_already_at_top(self, auth_client):
        """Moving the topmost task up should say 'Already at top'"""
        _, (task1_id, _) = self._setup_week_and_tasks(auth_client, num_tasks=2)
        response = auth_client.post(f"/api/tasks/{task1_id}/move-up")
        assert response.status_code == 200
        assert response.json()["message"] == "Already at top"

    def test_move_task_down(self, auth_client):
        """POST /api/tasks/{id}/move-down swaps sort_order with the task below"""
        _, (task1_id, task2_id) = self._setup_week_and_tasks(auth_client, num_tasks=2)

        response = auth_client.post(f"/api/tasks/{task1_id}/move-down")
        assert response.status_code == 200
        assert response.json()["message"] == "Moved down"

    def test_move_task_down_already_at_bottom(self, auth_client):
        """Moving the bottom task down should say 'Already at bottom'"""
        _, (_, task2_id) = self._setup_week_and_tasks(auth_client, num_tasks=2)
        response = auth_client.post(f"/api/tasks/{task2_id}/move-down")
        assert response.status_code == 200
        assert response.json()["message"] == "Already at bottom"

    def test_list_all_tasks(self, auth_client):
        """GET /api/tasks returns all tasks for the user across all weeks"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]
        auth_client.post("/api/tasks", json={"title": "T1", "week_id": week_id})
        auth_client.post("/api/tasks", json={"title": "T2", "week_id": week_id})

        response = auth_client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_task_api_prefix(self, auth_client):
        """GET /api/tasks/{id} returns the task"""
        _, (task_id,) = self._setup_week_and_tasks(auth_client, num_tasks=1)
        response = auth_client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["id"] == task_id

    def test_quick_add_task(self, auth_client):
        """POST /api/quick-add with a task entry string creates a task"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]

        response = auth_client.post(
            "/api/quick-add",
            data={"text": "P1 Deploy new feature", "week_id": week_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "task"
        assert "task_id" in data

    def test_quick_add_time_log(self, auth_client):
        """POST /api/quick-add with a time entry string creates a work entry"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]

        response = auth_client.post(
            "/api/quick-add",
            data={"text": "2h worked on bug fix", "week_id": week_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "time_log"
        assert data["minutes"] == 120


class TestListWorkEntriesAPI:
    """Tests for GET /api/work_entries (list all user work entries)"""

    def test_list_all_work_entries(self, auth_client):
        """GET /api/work_entries returns all entries for the user"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]

        task_resp = auth_client.post(
            "/api/tasks", json={"title": "My Task", "week_id": week_id}
        )
        task_id = task_resp.json()["id"]

        today = date.today()
        auth_client.post(
            "/api/work_entries",
            json={"task_id": task_id, "date": today.isoformat(), "minutes": 60}
        )
        auth_client.post(
            "/api/work_entries",
            json={"task_id": task_id, "date": today.isoformat(), "minutes": 90}
        )

        response = auth_client.get("/api/work_entries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_work_entries_empty(self, auth_client):
        """GET /api/work_entries returns empty list when no entries exist"""
        response = auth_client.get("/api/work_entries")
        assert response.status_code == 200
        assert response.json() == []


class TestWeekCSVExport:
    """Tests for GET /api/weeks/{week_id}/export"""

    def test_export_week_csv(self, auth_client):
        """Export returns a CSV file with correct content-type and rows"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]

        task_resp = auth_client.post(
            "/api/tasks", json={"title": "Export Task", "week_id": week_id}
        )
        task_id = task_resp.json()["id"]

        today = date.today()
        auth_client.post(
            "/api/work_entries",
            json={"task_id": task_id, "date": today.isoformat(), "minutes": 45,
                  "note": "Test note"}
        )

        response = auth_client.get(f"/api/weeks/{week_id}/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

        lines = response.text.strip().splitlines()
        assert lines[0] == "date,task,project,minutes,hours,start_time,end_time,note"
        assert len(lines) == 2  # header + 1 data row
        assert "Export Task" in lines[1]
        assert "45" in lines[1]

    def test_export_week_csv_no_entries(self, auth_client):
        """Export of a week with no work entries returns only header row"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_resp = auth_client.post(
            "/api/weeks", json={"start_date": week_start.isoformat()}
        )
        week_id = week_resp.json()["id"]

        response = auth_client.get(f"/api/weeks/{week_id}/export")
        assert response.status_code == 200
        lines = response.text.strip().splitlines()
        assert len(lines) == 1  # header only

    def test_export_week_not_found(self, auth_client):
        """Export of a non-existent week returns 404"""
        response = auth_client.get("/api/weeks/99999/export")
        assert response.status_code == 404


class TestProjectSoftDelete:
    """Tests that project delete is a soft-delete"""

    def test_delete_project_sets_inactive(self, auth_client):
        """DELETE /api/projects/{id} sets is_active=False, not removes row"""
        proj_resp = auth_client.post(
            "/api/projects", json={"name": "SoftDelete Project"}
        )
        proj_id = proj_resp.json()["id"]

        # Delete it
        del_resp = auth_client.delete(f"/api/projects/{proj_id}")
        assert del_resp.status_code == 200

        # It should now be excluded from the default active-only list
        list_resp = auth_client.get("/api/projects")
        names = [p["name"] for p in list_resp.json()]
        assert "SoftDelete Project" not in names

        # But visible when requesting all projects (active_only=false)
        all_resp = auth_client.get("/api/projects?active_only=false")
        all_names = [p["name"] for p in all_resp.json()]
        assert "SoftDelete Project" in all_names

    def test_deleted_project_is_inactive(self, auth_client):
        """The soft-deleted project has is_active=False"""
        proj_resp = auth_client.post(
            "/api/projects", json={"name": "Inactive Project"}
        )
        proj_id = proj_resp.json()["id"]
        auth_client.delete(f"/api/projects/{proj_id}")

        all_resp = auth_client.get("/api/projects?active_only=false")
        proj = next(p for p in all_resp.json() if p["id"] == proj_id)
        assert proj["is_active"] is False
