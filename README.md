# Notetime

A notebook-style weekly task planner and time tracker.

Plan tasks at the start of the week, log time as you work, and review a grouped summary at the end of the week.

---

## Beta Testing

Notetime is currently in closed beta. If you have been invited to test the app:

- **No installation required** — the app runs in your browser.
- See [BETA-TESTING.md](BETA-TESTING.md) for a full guide covering the core workflow, quick-add syntax, keyboard shortcuts, and how to submit feedback.
- See [KNOWN-ISSUES.md](KNOWN-ISSUES.md) for the current list of known gaps and workarounds.
- Submit feedback at `/feedback` inside the app (no login required).

---

## Core Concepts

- Tasks are planned intent — they belong to a week
- Work entries record actual time spent on a task
- Active and delegated tasks carry forward automatically to the next week
- The weekly summary groups time by project, rounded to the nearest 15 minutes

---

## Tech Stack

- Python / FastAPI
- SQLAlchemy with PostgreSQL (Neon for serverless production, SQLite for local dev)
- Pydantic v2
- HTMX (server-rendered partials)
- Jinja2 templates

---

## Running Locally (Development)

### Option 1: Docker (recommended for contributors)

Starts the web app and a PostgreSQL database together.

```bash
docker-compose up -d
```

Then open: http://localhost:8000

See [DOCKER.md](DOCKER.md) for full Docker documentation.

> **Note:** Docker is used internally by the development team and for superuser testing. External beta testers use the deployed web app — no local setup needed.

### Option 2: Python (SQLite)

```bash
pip install -r requirements.txt
python -m notetime.seed   # optional sample data
uvicorn notetime.main:app --reload
```

Then open: http://localhost:8000

Set environment variables (copy `.env.example` to `.env`):

```
SECRET_KEY=<random-64-char-string>
COOKIE_SECURE=false   # for local HTTP only
```

### API Docs

With the server running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Help: http://localhost:8000/api/help

---

## Running Tests

```bash
pytest
pytest --cov=notetime   # with coverage
```

The test suite requires `SECRET_KEY` and `COOKIE_SECURE=false` to be set. These are injected automatically via `pyproject.toml` when running `pytest`.

---

## Deployment

Multiple deployment options are available:

- **Neon (Serverless PostgreSQL)** - Recommended for modern deployments. See [NEON-DEPLOYMENT.md](NEON-DEPLOYMENT.md) for step-by-step setup with autoscaling, instant provisioning, and database branching.
- **Render.com** - Traditional deployment. See [DEPLOYMENT.md](DEPLOYMENT.md) for setup instructions.

---

## Feedback

File issues or feature requests via the in-app feedback form at `/feedback`, or contact the team directly.
