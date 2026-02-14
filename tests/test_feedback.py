"""
Tests for feedback form and API endpoints.

Run with: pytest tests/test_feedback.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from notetime.main import app
from notetime.models import Base, Feedback
from notetime.db import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db():
    """In-memory SQLite database for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    return TestClient(app, follow_redirects=True)


@pytest.fixture
def auth_client(test_db):
    """Client with a registered and logged-in user."""
    c = TestClient(app, follow_redirects=True)
    c.post(
        "/api/auth/register",
        json={"email": "beta@example.com", "username": "betatester", "password": "password123"},
    )
    resp = c.post(
        "/auth/login",
        data={"username": "betatester", "password": "password123"},
    )
    # Cookie is set automatically by TestClient
    return c


# ---------------------------------------------------------------------------
# Feedback form page
# ---------------------------------------------------------------------------

class TestFeedbackPage:
    def test_get_feedback_form_anonymous(self, client):
        """Anonymous users can access the feedback form."""
        response = client.get("/feedback")
        assert response.status_code == 200
        assert "Beta Feedback Form" in response.text
        assert "feedback-form" in response.text

    def test_get_feedback_form_authenticated(self, auth_client):
        """Authenticated users see the form pre-filled with their email."""
        response = auth_client.get("/feedback")
        assert response.status_code == 200
        assert "beta@example.com" in response.text

    def test_feedback_page_contains_all_categories(self, client):
        """Form must expose all five feedback categories."""
        response = client.get("/feedback")
        for category in ["bug_report", "feature_request", "ui_ux", "performance", "general"]:
            assert category in response.text

    def test_feedback_page_contains_severity_options(self, client):
        response = client.get("/feedback")
        for level in ["critical", "high", "medium", "low"]:
            assert level in response.text

    def test_feedback_page_contains_reproducibility_options(self, client):
        response = client.get("/feedback")
        for freq in ["always", "sometimes", "rarely"]:
            assert freq in response.text


# ---------------------------------------------------------------------------
# Feedback form submission
# ---------------------------------------------------------------------------

class TestFeedbackFormSubmission:
    def test_submit_minimal_feedback(self, client):
        """Submitting only required fields returns success page."""
        response = client.post(
            "/feedback",
            data={
                "category": "general",
                "title": "Great app!",
                "description": "Really enjoying the beta so far.",
            },
        )
        assert response.status_code == 200
        assert "Thank you for your feedback" in response.text

    def test_submit_full_bug_report(self, client):
        """Submitting all bug-report fields is accepted."""
        response = client.post(
            "/feedback",
            data={
                "category": "bug_report",
                "title": "Task completion button unresponsive",
                "description": "Clicking Complete does nothing on Firefox 121.",
                "severity": "high",
                "reproducibility": "always",
                "browser_info": "Firefox 121 on Ubuntu 22.04",
                "rating": "3",
                "contact_email": "user@example.com",
            },
        )
        assert response.status_code == 200
        assert "Thank you for your feedback" in response.text

    def test_submit_feature_request_with_rating(self, client):
        response = client.post(
            "/feedback",
            data={
                "category": "feature_request",
                "title": "Add dark mode",
                "description": "A dark theme would reduce eye strain at night.",
                "rating": "5",
            },
        )
        assert response.status_code == 200
        assert "Thank you" in response.text

    def test_missing_title_returns_error(self, client):
        response = client.post(
            "/feedback",
            data={
                "category": "general",
                "title": "   ",
                "description": "Some description.",
            },
        )
        assert response.status_code == 422
        assert "Title is required" in response.text

    def test_missing_description_returns_error(self, client):
        response = client.post(
            "/feedback",
            data={
                "category": "general",
                "title": "Valid title",
                "description": "   ",
            },
        )
        assert response.status_code == 422
        assert "Description is required" in response.text

    def test_invalid_category_returns_error(self, client):
        response = client.post(
            "/feedback",
            data={
                "category": "not_a_real_category",
                "title": "Test",
                "description": "Test description.",
            },
        )
        assert response.status_code == 422
        assert "valid feedback category" in response.text

    def test_title_too_long_returns_error(self, client):
        response = client.post(
            "/feedback",
            data={
                "category": "general",
                "title": "x" * 201,
                "description": "Some description.",
            },
        )
        assert response.status_code == 422

    def test_anonymous_feedback_stored_without_user_id(self, client, test_db):
        client.post(
            "/feedback",
            data={
                "category": "general",
                "title": "Anonymous feedback",
                "description": "No account needed.",
            },
        )
        db = test_db()
        feedback = db.query(Feedback).filter(Feedback.title == "Anonymous feedback").first()
        db.close()
        assert feedback is not None
        assert feedback.user_id is None

    def test_authenticated_feedback_stores_user_id(self, auth_client, test_db):
        auth_client.post(
            "/feedback",
            data={
                "category": "ui_ux",
                "title": "Logged-in feedback",
                "description": "Submitted while authenticated.",
            },
        )
        db = test_db()
        feedback = db.query(Feedback).filter(Feedback.title == "Logged-in feedback").first()
        db.close()
        assert feedback is not None
        assert feedback.user_id is not None


# ---------------------------------------------------------------------------
# JSON API endpoint
# ---------------------------------------------------------------------------

class TestFeedbackAPI:
    def test_api_submit_feedback(self, client):
        """POST /api/feedback returns 201 with created feedback."""
        response = client.post(
            "/api/feedback",
            json={
                "category": "performance",
                "title": "App feels slow on large weeks",
                "description": "Loading a week with 50 tasks takes ~3 seconds.",
                "rating": 2,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "performance"
        assert data["title"] == "App feels slow on large weeks"
        assert data["rating"] == 2
        assert data["status"] == "new"
        assert "id" in data
        assert "submitted_at" in data

    def test_api_submit_full_bug_report(self, client):
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug_report",
                "title": "Crash on login",
                "description": "500 error when logging in with special chars.",
                "severity": "critical",
                "reproducibility": "always",
                "browser_info": "Safari 17 on iOS 17",
                "contact_email": "reporter@example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["severity"] == "critical"
        assert data["reproducibility"] == "always"

    def test_api_missing_required_fields(self, client):
        response = client.post(
            "/api/feedback",
            json={"category": "general"},
        )
        assert response.status_code == 422

    def test_api_invalid_rating(self, client):
        response = client.post(
            "/api/feedback",
            json={
                "category": "general",
                "title": "Rating out of range",
                "description": "Test.",
                "rating": 10,
            },
        )
        assert response.status_code == 422

    def test_api_invalid_category(self, client):
        response = client.post(
            "/api/feedback",
            json={
                "category": "spam",
                "title": "Test",
                "description": "Test.",
            },
        )
        assert response.status_code == 422

    def test_list_feedback_requires_auth(self, client):
        """GET /api/feedback is protected."""
        response = client.get("/api/feedback")
        assert response.status_code in (401, 303)

    def test_list_feedback_returns_user_submissions(self, auth_client):
        """Authenticated user only sees their own feedback."""
        auth_client.post(
            "/api/feedback",
            json={
                "category": "general",
                "title": "My feedback",
                "description": "Test.",
            },
        )
        response = auth_client.get("/api/feedback")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(item["user_id"] is not None for item in data)

    def test_feedback_status_defaults_to_new(self, client):
        response = client.post(
            "/api/feedback",
            json={
                "category": "general",
                "title": "Default status test",
                "description": "Should default to new.",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "new"
