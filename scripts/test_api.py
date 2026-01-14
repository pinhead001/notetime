#!/usr/bin/env python3
"""
API Test Script - Day 6

Tests all FastAPI endpoints to verify they work correctly.

Usage:
    # Start the API server in one terminal:
    uvicorn notetime.main:app --reload

    # Run this test script in another terminal:
    python scripts/test_api.py
"""
import sys
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from datetime import date
from fastapi.testclient import TestClient
from notetime.main import app
from notetime.db import engine
from notetime.models import Base

# Create test client
client = TestClient(app)


def reset_database():
    """Reset database for clean testing"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("✓ Database reset\n")


def test_health_check():
    """Test health endpoints"""
    print("Testing health check...")
    response = client.get("/")
    assert response.status_code == 200
    assert "Notetime API" in response.json()["message"]

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✓ Health check passed\n")


def test_create_week():
    """Test creating a week"""
    print("Testing week creation...")
    response = client.post(
        "/weeks",
        params={"start_date": "2024-01-08", "note": "Test week"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["start_date"] == "2024-01-08"
    assert data["note"] == "Test week"
    assert "id" in data

    week_id = data["id"]
    print(f"✓ Created week {week_id}\n")
    return week_id


def test_get_current_week():
    """Test getting current week (auto-creates if needed)"""
    print("Testing current week endpoint...")
    response = client.get("/weeks/current")
    assert response.status_code == 200
    data = response.json()
    assert "week" in data
    assert "tasks" in data
    assert "summary" in data
    print(f"✓ Current week retrieved: {data['week']['start_date']}\n")
    return data["week"]["id"]


def test_create_project():
    """Test creating a project"""
    print("Testing project creation...")
    response = client.post(
        "/projects",
        params={"name": "Test Project", "is_active": True}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["is_active"] == True

    project_id = data["id"]
    print(f"✓ Created project {project_id}: {data['name']}\n")
    return project_id


def test_list_projects():
    """Test listing projects"""
    print("Testing project listing...")
    response = client.get("/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) >= 1
    print(f"✓ Found {len(projects)} project(s)\n")


def test_create_task(week_id, project_id):
    """Test creating a task"""
    print("Testing task creation...")
    task_data = {
        "title": "Test Task",
        "week_id": week_id,
        "state": "active",
        "priority": 1,
        "project_id": project_id,
        "delegate": None
    }
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["state"] == "active"
    assert data["priority"] == 1

    task_id = data["id"]
    print(f"✓ Created task {task_id}: {data['title']}\n")
    return task_id


def test_get_task(task_id):
    """Test getting a specific task"""
    print(f"Testing task retrieval (id={task_id})...")
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    print(f"✓ Retrieved task: {data['title']}\n")


def test_update_task(task_id):
    """Test updating a task"""
    print(f"Testing task update (id={task_id})...")
    response = client.put(
        f"/tasks/{task_id}",
        params={
            "title": "Updated Task Title",
            "state": "completed",
            "priority": 2
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["state"] == "completed"
    assert data["priority"] == 2
    print(f"✓ Updated task: {data['title']} (state: {data['state']})\n")


def test_create_work_entry(task_id):
    """Test creating a work entry"""
    print("Testing work entry creation...")
    entry_data = {
        "task_id": task_id,
        "date": "2024-01-08",
        "minutes": 120,
        "note": "Test work session"
    }
    response = client.post("/work_entries", json=entry_data)
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == task_id
    assert data["minutes"] == 120

    entry_id = data["id"]
    print(f"✓ Created work entry {entry_id}: {data['minutes']} minutes\n")
    return entry_id


def test_get_work_entry(entry_id):
    """Test getting a work entry"""
    print(f"Testing work entry retrieval (id={entry_id})...")
    response = client.get(f"/work_entries/{entry_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry_id
    print(f"✓ Retrieved work entry: {data['minutes']} minutes\n")


def test_get_week_view(week_id):
    """Test getting full week view"""
    print(f"Testing weekly view (week_id={week_id})...")
    response = client.get(f"/weeks/{week_id}")
    assert response.status_code == 200
    data = response.json()

    assert "week" in data
    assert "tasks" in data
    assert "work_entries" in data
    assert "projects" in data
    assert "summary" in data

    print(f"✓ Weekly view retrieved:")
    print(f"  - Week: {data['week']['start_date']}")
    print(f"  - Tasks: {len(data['tasks'])}")
    print(f"  - Work entries: {len(data['work_entries'])}")
    print(f"  - Projects: {len(data['projects'])}")
    print(f"  - Summary: {len(data['summary'])} projects\n")


def test_error_handling():
    """Test error responses"""
    print("Testing error handling...")

    # Test 404 - task not found
    response = client.get("/tasks/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test 404 - week not found
    response = client.get("/weeks/99999")
    assert response.status_code == 404

    # Test 422 - invalid minutes (negative)
    response = client.post("/work_entries", json={
        "task_id": 1,
        "date": "2024-01-08",
        "minutes": -10,  # Invalid!
        "note": "test"
    })
    assert response.status_code == 422

    print("✓ Error handling works correctly\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("FASTAPI CRUD ENDPOINT TESTS - DAY 6")
    print("=" * 60)
    print()

    # Reset database
    reset_database()

    # Run tests in sequence
    test_health_check()

    week_id = test_create_week()
    current_week_id = test_get_current_week()

    project_id = test_create_project()
    test_list_projects()

    task_id = test_create_task(week_id, project_id)
    test_get_task(task_id)
    test_update_task(task_id)

    entry_id = test_create_work_entry(task_id)
    test_get_work_entry(entry_id)

    test_get_week_view(week_id)

    test_error_handling()

    # Summary
    print("=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("API Endpoints Tested:")
    print("  ✓ POST   /weeks")
    print("  ✓ GET    /weeks/current")
    print("  ✓ GET    /weeks/{id}")
    print("  ✓ POST   /projects")
    print("  ✓ GET    /projects")
    print("  ✓ POST   /tasks")
    print("  ✓ GET    /tasks/{id}")
    print("  ✓ PUT    /tasks/{id}")
    print("  ✓ POST   /work_entries")
    print("  ✓ GET    /work_entries/{id}")
    print("  ✓ GET    /")
    print("  ✓ GET    /health")
    print()
    print("View API docs at: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()
