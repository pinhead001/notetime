# Notetime

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

### Option 1: Docker (Recommended for Local Development)

The easiest way to run Notetime locally with PostgreSQL:

```bash
# Start all services (web app + database)
docker-compose up -d

# Initialize database with sample data
docker-compose exec web python -m notetime.seed
```

Then open your browser to: http://localhost:8000

See [DOCKER.md](DOCKER.md) for complete Docker documentation.

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
