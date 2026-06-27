# Scryve Backend

Production-ready FastAPI foundation for **Scryve**, an AI-powered Talent
Intelligence platform. This phase ships the scaffolding only — no candidate,
job, AI or ranking modules yet.

## Stack

- **Python** 3.12+
- **FastAPI** + Uvicorn
- **SQLAlchemy 2.0** ORM with **PostgreSQL**
- **Alembic** for migrations
- **Pydantic v2** + `pydantic-settings` for config and validation
- **JWT** auth utilities (`python-jose`) with role-based access scaffolding
- **structlog** for structured, request-scoped logging

## Project layout

```
backend/
├── app/
│   ├── api/                 # HTTP routers (versioned)
│   │   └── v1/
│   │       ├── endpoints/   # Route handlers (no business logic)
│   │       └── router.py
│   ├── core/                # Cross-cutting concerns (logging, security, errors)
│   ├── config/              # Pydantic Settings
│   ├── database/            # Engine, session factory, declarative base
│   ├── dependencies/        # FastAPI Depends providers
│   ├── middleware/          # Request logging + global exception handlers
│   ├── models/              # SQLAlchemy ORM models
│   ├── repositories/        # Data-access abstractions (repository pattern)
│   ├── schemas/             # Pydantic request/response models
│   ├── services/            # Business-logic orchestration
│   ├── utils/               # Generic helpers
│   └── main.py              # FastAPI application factory
├── migrations/              # Alembic environment + versions
├── tests/                   # Pytest suite
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Getting started

### 1. Configure environment

```bash
cp .env.example .env
# edit values, especially JWT_SECRET_KEY and POSTGRES_*
```

### 2. Local development (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate         # PowerShell / cmd
pip install -r requirements.txt

# Ensure PostgreSQL is reachable per .env, then:
alembic upgrade head
uvicorn app.main:app --reload
```

The API is served at <http://localhost:8000>, with interactive docs at
`/docs` (Swagger) and `/redoc`.

### 3. With Docker Compose

```bash
docker compose up --build
```

This launches PostgreSQL plus the API container. Migrations run automatically
on startup.

## Health checks

| Endpoint            | Purpose                                  |
| ------------------- | ---------------------------------------- |
| `GET /api/v1/health`    | Liveness probe                           |
| `GET /api/v1/health/db` | Readiness probe (verifies DB connection) |

## Architecture rules

- **Repository pattern**: data access lives in `app/repositories`, never in
  routers or services directly.
- **Layer separation**: routers call services, services call repositories.
  Routes contain no business logic.
- **Dependency injection** via `fastapi.Depends` (DB session, auth payload,
  role guards).
- **Type hints everywhere**, Google-style docstrings.
- **Async endpoints** by default; sync work is offloaded to threadpool by
  FastAPI when needed.

## Testing

```bash
pytest
```

## Migrations

```bash
# Create a migration after editing models
alembic revision --autogenerate -m "add candidates table"

# Apply
alembic upgrade head
```

See `migrations/README.md` for more.
