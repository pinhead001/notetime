# Testing Instructions for Merged Branch

This document provides step-by-step instructions for testing the merged changes in the `claude/fix-task-init-error-KjgCH` branch.

## Recent Changes Summary

The following changes have been merged:
- Fixed password hashing in seed script
- Auto-create database tables in seed script
- Added Docker support for local development
- Improved password hashing with SHA256 pre-hash
- Enhanced JWT handling

## Prerequisites

### Option 1: Docker Testing (Recommended)
- Docker (version 20.10 or later)
- Docker Compose (version 2.0 or later)

Verify installation:
```bash
docker --version
docker-compose --version
```

### Option 2: Local Python Testing
- Python 3.9+
- pip

## Testing Procedure

### A. Docker-Based Testing

#### 1. Pull Latest Changes

```bash
# Ensure you're on the correct branch
git checkout claude/fix-task-init-error-KjgCH
git pull origin claude/fix-task-init-error-KjgCH
```

#### 2. Clean Start (Remove Previous Containers/Volumes)

```bash
# Stop and remove existing containers and volumes
docker-compose down -v

# Remove any orphaned containers
docker-compose rm -f
```

#### 3. Build and Start Services

```bash
# Build and start in detached mode
docker-compose up -d --build

# View logs to ensure services started correctly
docker-compose logs -f
```

Expected output:
- PostgreSQL should start and become healthy
- FastAPI app should start on port 8000

Press `Ctrl+C` to stop following logs (containers continue running).

#### 4. Initialize Database with Seed Data

```bash
# Run the seed script (tests auto-create tables fix)
docker-compose exec web python -m notetime.seed
```

**Expected output:**
- "Database tables created successfully" or similar message
- Message showing default user credentials (e.g., "user@example.com / password")
- No errors about missing tables or password hashing

**This tests:**
- Auto-create database tables functionality
- Fixed password hashing in seed script

#### 5. Run Automated Tests

```bash
# Run all tests
docker-compose exec web pytest

# Run with coverage report
docker-compose exec web pytest --cov=notetime

# Run specific test suites
docker-compose exec web pytest tests/test_api_auth.py  # Auth tests
docker-compose exec web pytest tests/test_time_engine.py  # Time engine tests
docker-compose exec web pytest tests/test_api_main.py  # Main API tests
```

**Expected results:**
- All tests should pass
- No authentication-related failures
- Coverage report should display (if using --cov)

#### 6. Manual Testing - Web Interface

Open your browser to: http://localhost:8000

**Test 1: User Authentication**
1. Navigate to http://localhost:8000
2. Log in with credentials from seed output (default: `user@example.com` / `password`)
3. Verify successful login
4. Check that you're redirected to the main dashboard

**This tests:**
- Password hashing fixes
- JWT token generation
- Authentication system

**Test 2: Task Management**
1. Create a new task
2. View task list
3. Complete a task
4. Delete a task

**Test 3: Weekly Planning**
1. Navigate to weekly view
2. Add tasks to current week
3. Log work entries
4. Verify weekly summary displays correctly

**Test 4: API Documentation**
1. Navigate to http://localhost:8000/docs (Swagger UI)
2. Test the `/token` endpoint with seed user credentials
3. Copy the access token
4. Use "Authorize" button to authenticate
5. Test protected endpoints (e.g., `/tasks/`, `/weeks/`)

**Expected results:**
- All operations should work without errors
- Authentication should succeed with hashed passwords
- JWT tokens should be generated correctly

#### 7. Check Logs for Errors

```bash
# Check application logs
docker-compose logs web | grep -i error

# Check database logs
docker-compose logs db | grep -i error
```

**Expected results:**
- No critical errors
- No password hashing errors
- No database connection errors

#### 8. Database Verification

```bash
# Access PostgreSQL shell
docker-compose exec db psql -U notetime -d notetime
```

Run these SQL commands:
```sql
-- Verify tables exist
\dt

-- Check users table and password hashing
SELECT id, email, LENGTH(hashed_password) as hash_length FROM users;

-- Check tasks exist
SELECT COUNT(*) FROM tasks;

-- Exit
\q
```

**Expected results:**
- All required tables exist (users, tasks, weeks, work_entries)
- User passwords are properly hashed (hash_length should be 60-80 characters for bcrypt)
- Seed data is present

#### 9. Cleanup (After Testing)

```bash
# Stop services
docker-compose down

# Or remove volumes too (clean slate)
docker-compose down -v
```

---

### B. Local Python Testing

#### 1. Pull Latest Changes

```bash
git checkout claude/fix-task-init-error-KjgCH
git pull origin claude/fix-task-init-error-KjgCH
```

#### 2. Setup Python Environment

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (default SQLite is fine for testing)
```

#### 4. Initialize Database

```bash
# Remove old database if exists
rm -f notetime.db

# Run seed script (tests auto-create tables)
python -m notetime.seed
```

**Expected output:**
- Database file created (notetime.db)
- Tables auto-created
- Seed user created with hashed password
- Credentials displayed

#### 5. Run Automated Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=notetime

# Run specific tests
pytest tests/test_api_auth.py
pytest tests/test_time_engine.py
```

**Expected results:**
- All tests pass
- No authentication failures

#### 6. Start Application

```bash
# Start FastAPI server
uvicorn notetime.main:app --reload
```

#### 7. Manual Testing

Follow the same manual testing steps as Docker (Section A.6), using http://localhost:8000

#### 8. Database Verification (SQLite)

```bash
# Install sqlite3 if not available
# Ubuntu/Debian: sudo apt-get install sqlite3
# macOS: (pre-installed)

# Open database
sqlite3 notetime.db

# Run verification queries
.tables
.schema users
SELECT id, email, length(hashed_password) FROM users;
SELECT COUNT(*) FROM tasks;
.quit
```

#### 9. Cleanup

```bash
# Stop server (Ctrl+C)
# Deactivate virtual environment
deactivate

# Remove test database
rm -f notetime.db
```

---

## Verification Checklist

Use this checklist to confirm all critical functionality works:

- [ ] Docker containers build and start successfully
- [ ] Database tables are auto-created by seed script
- [ ] Seed script completes without errors
- [ ] User passwords are properly hashed (bcrypt format)
- [ ] All automated tests pass
- [ ] User can log in with seed credentials
- [ ] JWT tokens are generated correctly
- [ ] Protected API endpoints require authentication
- [ ] Tasks can be created, viewed, updated, and deleted
- [ ] Weekly planning features work
- [ ] No errors in application logs
- [ ] API documentation is accessible and functional

## Common Issues and Solutions

### Issue: Port 8000 Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find and kill the process using port 8000
lsof -i :8000
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Issue: Database Connection Failed

**Error:** `could not connect to server`

**Solution:**
```bash
# Wait for database to be ready
docker-compose logs db

# Restart services
docker-compose restart
```

### Issue: Password Hash Error

**Error:** Related to password hashing in logs

**Solution:**
- Verify `passlib[bcrypt]` is installed: `pip list | grep passlib`
- Rebuild Docker containers: `docker-compose build --no-cache`
- Check seed script imports are correct

### Issue: Tests Fail

**Solution:**
```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/test_api_auth.py -v -s

# Check test database is clean
rm -f test_notetime.db
```

## Smoke Test (Quick Verification)

If you need a quick verification that everything works:

```bash
# 1. Start services
docker-compose up -d --build

# 2. Initialize database
docker-compose exec web python -m notetime.seed

# 3. Run tests
docker-compose exec web pytest

# 4. Check web interface
curl http://localhost:8000

# 5. Test authentication
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password"

# 6. Cleanup
docker-compose down
```

All commands should succeed without errors.

## Reporting Issues

If you encounter any issues during testing:

1. Capture error messages and logs
2. Note the testing method used (Docker vs Local)
3. Include steps to reproduce
4. Check existing issues or create a new one

---

**Testing Document Version:** 1.0
**Last Updated:** 2026-02-10
**Branch:** claude/fix-task-init-error-KjgCH
