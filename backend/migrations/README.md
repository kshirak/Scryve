# Alembic Migrations

Database schema is managed with Alembic. The Alembic environment is wired to
the application's Pydantic settings, so the same configuration drives the API
and the migrations.

## Common commands

Run from inside `backend/` with your `.env` loaded:

```bash
# Generate a new migration after editing ORM models
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back the most recent migration
alembic downgrade -1

# Show current revision
alembic current
```
