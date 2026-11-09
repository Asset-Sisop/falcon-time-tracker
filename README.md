# Falcon Time Tracker

A compact employee time-tracking web application built for the Falcon AI programming assignment.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · vanilla JavaScript · Docker Compose · Pytest

## Features

- Create and list employees; optional unique email.
- Start a work timer with a task name and optional description.
- One active timer per employee. A second start request returns HTTP `409 Conflict`.
- Stop a timer; a second stop request returns HTTP `409 Conflict`.
- Persistent work sessions stored in PostgreSQL.
- Session history filtered by employee and date range.
- Per-employee report with total time and session count for the selected period.
- Report duration is clipped to the selected time window; a running timer is calculated through the current time.
- Responsive Russian-language interface and OpenAPI documentation.

All sample data must be fictional. The app starts with an empty database.

## Run with Docker Compose

Requirements: Docker Engine/Desktop with the Compose plugin.

```bash
cp .env.example .env
# Edit .env and set a strong POSTGRES_PASSWORD.
docker compose up --build -d
```

Open `http://localhost:8088`, API docs at `/docs`, and health check at `/health`.

Stop without deleting data with `docker compose down`. The PostgreSQL volume is retained. To delete it as well (destructive), run `docker compose down -v`.

## Run locally without Docker

Python 3.12+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The default local database is SQLite (`./time_tracker.db`). Open `http://127.0.0.1:8000`.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/employees` | Create employee |
| `GET` | `/api/employees` | List employees |
| `DELETE` | `/api/employees/{id}` | Delete employee and sessions |
| `POST` | `/api/employees/{id}/timer/start` | Start timer |
| `POST` | `/api/sessions/{id}/stop` | Stop timer |
| `GET` | `/api/sessions` | List sessions; optional `employee_id`, `date_from`, `date_to` |
| `GET` | `/api/reports` | Employee totals; required `date_from`, `date_to` |
| `GET` | `/api/summary` | Employee and active timer counts |
| `GET` | `/health` | Health check |

Interactive API documentation: `/docs`.

## Tests

Tests use an isolated in-memory SQLite database and do not require PostgreSQL:

```bash
pip install -r requirements.txt
pytest -q
```

Covered scenarios: employee creation/listing, timer start/stop, duplicate start (`409`), duplicate stop (`409`), empty report, invalid report range, and unknown employee (`404`).

## AI-assisted development notes

This project was developed with **ChatGPT (GPT-6)** as an AI coding assistant. AI was used to draft the project structure, API endpoints, SQLAlchemy models, frontend interactions, Docker configuration, tests and documentation. The implementation was reviewed and refined against the assignment requirements.

Human review covered the API contract, SQLAlchemy models, timer state transitions, duplicate-start protection, report date-window calculations, frontend behavior and test assertions. The automated test suite was run locally with pytest; the recorded result was **7 passed**. Docker image build and public deployment remain to be verified in the target environment.

### Example prompts used

1. "Design a minimal FastAPI + SQLAlchemy employee time-tracking API. Enforce one active timer per employee and return HTTP 409 for a duplicate start, including concurrent requests."
2. "Implement report aggregation for a selected date/time range. Clip sessions to the report boundaries and include currently running sessions through the current UTC time."
3. "Write pytest tests for employee creation, timer start/stop, duplicate start, duplicate stop, empty reports and invalid date ranges."
4. "Review this implementation for timezone, persistence, validation and race-condition issues. Explain each issue and propose a minimal correction."

## Engineering review / known limitations

- Duplicate active timers are rejected by API validation and a partial unique database index on `employee_id WHERE stopped_at IS NULL`; concurrent attempts are translated to HTTP `409 Conflict`.
- Employees with zero activity are included in reports.
- Session history filters by session start time. Report totals clip overlapping work time to the requested window.
- Authentication, authorization, audit log, backups, migrations and multi-tenant isolation are outside this small assignment's scope.
- Database schema is created on startup for this demo. Use Alembic migrations for production evolution.

## Deployment notes

The Compose stack binds the application to port `8088` by default. For public access, deploy behind a TLS-terminating reverse proxy (for example, Nginx/Caddy), configure DNS and HTTPS, and set a strong secret in `.env`. Do not expose PostgreSQL publicly.

## License

MIT
