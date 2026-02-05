# Notetime

![Docker Build](https://github.com/pinhead001/notetime/actions/workflows/docker-publish.yml/badge.svg)

A notebook-style weekly task and time-tracking app.

## Core Concepts
- Tasks are planned intent
- Weeks define planning windows
- Work entries record actual time spent

## Tech stack
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- HTMX
- SQLite

## How to run

### Option 1: Docker (Recommended)

The easiest way to run Notetime is with Docker:

```bash
# Pull the latest image from GitHub Container Registry
docker pull ghcr.io/pinhead001/notetime:latest

# Run with Docker Compose (includes PostgreSQL)
docker-compose up -d

# Or run standalone with SQLite
docker run -d -p 8000:8000 ghcr.io/pinhead001/notetime:latest
```

Then open: http://localhost:8000

**See [DOCKER.md](DOCKER.md) for complete Docker documentation**
**Windows users:** See [DOCKER-WINDOWS.md](DOCKER-WINDOWS.md)

### Option 2: Local Python Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Seed the database with sample data:
```bash
python -m notetime.seed
```

### Run the web app

Start the FastAPI server with HTMX web interface:

```bash
uvicorn notetime.main:app --reload
```

Then open your browser to: http://localhost:8000

The web interface provides:
- Weekly task planning and tracking
- Daily work entry logging
- Automatic weekly summary generation
- Inline task actions (complete, delegate, defer)

### API Documentation

With the server running, view the auto-generated API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Demo scripts

Run demonstration scripts to see core functionality:

```bash
# Weekly summary generation
python -m scripts.demo_summary

# Task rollover between weeks
python -m scripts.demo_rollover
```

### Run tests

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_time_engine.py
pytest tests/test_summary.py
pytest tests/test_rollover.py

# Run with coverage
pytest --cov=notetime
```

## Published Docker Images

Pre-built Docker images are automatically published to GitHub Container Registry:

- **Latest:** `ghcr.io/pinhead001/notetime:latest`
- **Versioned:** `ghcr.io/pinhead001/notetime:1.0.0`

Images are built automatically on every push to main via GitHub Actions.

**See [GITHUB-ACTIONS.md](GITHUB-ACTIONS.md) for CI/CD documentation**

## Documentation

- [Docker Setup](DOCKER.md) - Complete Docker guide
- [Docker for Windows](DOCKER-WINDOWS.md) - Windows-specific instructions
- [GitHub Actions](GITHUB-ACTIONS.md) - CI/CD and image publishing
- [Git Instructions](GIT-instructions.md) - Branch management and merging
