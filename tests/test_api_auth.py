"""
Integration tests for authentication API endpoints

Run with: pytest tests/test_api_auth.py -v
"""
import pytest
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


class TestUserRegistration:
    """Test user registration endpoints"""

    def test_register_new_user(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert "id" in data

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser1",
                "password": "SecurePassword123"
            }
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser2",
                "password": "SecurePassword456"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client):
        """Test registration with duplicate username"""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "email": "test1@example.com",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )

        # Try to register with same username
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test2@example.com",
                "username": "testuser",
                "password": "SecurePassword456"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login endpoints"""

    def test_login_success(self, client):
        """Test successful login"""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )

        # Login
        response = client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
                "password": "SecurePassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
                "password": "WrongPassword"
            }
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword"
            }
        )
        assert response.status_code == 401

    def test_login_username_instead_of_email(self, client):
        """Test login using username instead of email"""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )

        # Login with username
        response = client.post(
            "/api/auth/login",
            data={
                "username": "testuser",
                "password": "SecurePassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestGetCurrentUser:
    """Test current user retrieval"""

    def test_get_current_user_authenticated(self, client):
        """Test getting current user with valid token"""
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

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
