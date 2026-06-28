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

## Phase 3 — Job Intelligence

Phase 3 turns a free-text job description into a structured, queryable,
embedding-backed record ready for Phase 4 matching.

### What it does

1. **Job persistence** — stores every job in the `jobs` table with the
   raw text plus 13 structured fields (required/preferred/soft skills,
   programming languages, tools/frameworks, domain knowledge,
   responsibilities, qualifications, education requirements,
   disqualifiers, extracted keywords, experience range / level,
   locations).
2. **NLP-based extraction** — `app/intelligence/parsers/job_extractor.py`
   uses the curated taxonomy (`app/intelligence/skills/`) and the
   existing `JDParser` heuristic to pull skills out of bullet lists
   *and* prose, bucket them by category, and assign an experience level
   (Junior / Mid / Senior / Staff / Principal).
3. **Skill normalization** — `SkillNormalizer` resolves aliases
   (`"Postgres"` → `"PostgreSQL"`, `"React.js"` → `"React"`,
   `"Py"` → `"Python"`, `"ML"` → `"Machine Learning"`, ...) using a
   hand-curated alias map with an optional `difflib` fuzzy fallback.
4. **Embedding generation** — `app/intelligence/embeddings/` ships two
   backends:
   - **Hashing (default)** — deterministic, dependency-free,
     L2-normalized vector ready for FAISS `IndexFlatIP`.
   - **Sentence-Transformers (optional)** — set
     `EMBEDDING_BACKEND=sentence-transformers` and install the package.

### Public service surface (`app.services.JobService`)

| Method                       | What it does                                                    |
| ---------------------------- | --------------------------------------------------------------- |
| `create_job_profile(payload)`| Extract, persist, and embed a JD in a single call.              |
| `extract_job_skills(text)`   | Run the extractor without writing to the database.              |
| `generate_job_embedding(id)` | (Re)build the embedding for an existing job.                    |
| `get_job_requirements(id)`   | Return the matching-ready `JobRequirements` view (Phase 4 IO).  |

### HTTP endpoints

| Method | Path                                  | Purpose                                       |
| ------ | ------------------------------------- | --------------------------------------------- |
| POST   | `/api/v1/jobs/extract`                | Extract structured fields without saving.     |
| POST   | `/api/v1/jobs`                        | Create a job (extract + persist + embed).     |
| GET    | `/api/v1/jobs`                        | List recently created jobs (paginated).       |
| GET    | `/api/v1/jobs/{id}`                   | Full job record including embedding metadata. |
| GET    | `/api/v1/jobs/{id}/requirements`      | Matching-ready requirement view.              |
| GET    | `/api/v1/jobs/{id}/raw-extraction`    | Raw extractor JSON (audit / debug).           |
| POST   | `/api/v1/jobs/{id}/embedding`         | Regenerate the embedding vector.              |
| GET    | `/api/v1/jobs/{id}/embedding`         | Fetch the embedding vector and metadata.      |

### Running Phase 3

```bash
# 1. Install deps (numpy is new in this phase)
pip install -r requirements.txt

# 2. Apply migrations (creates `jobs` and `job_embeddings`)
alembic upgrade head

# 3. Start the API
uvicorn app.main:app --reload

# 4. Try the extractor without persisting
curl -X POST http://localhost:8000/api/v1/jobs/extract \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"Looking for Python Django developer with PostgreSQL experience and REST API knowledge. 2-4 years experience required.\"}"

# 5. Create and persist a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Backend Developer\", \"description\": \"...full JD text...\"}"
```

### Configuration

The embedding backend is selectable via environment variables (see
`.env.example`):

```
EMBEDDING_BACKEND=hashing            # or "sentence-transformers"
EMBEDDING_MODEL_NAME=hashing-v1
EMBEDDING_DIMENSION=384
```

### Phase 3 tests

```bash
pytest tests/intelligence/test_skill_normalizer.py \
       tests/intelligence/test_job_extractor.py \
       tests/intelligence/test_job_embedder.py \
       tests/intelligence/test_job_service.py \
       tests/test_jobs_api.py
```

See [`docs/phase3_api.md`](docs/phase3_api.md) for the full HTTP contract.

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
