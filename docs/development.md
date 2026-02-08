# Development

This document is the default onboarding guide for contributors.

## Prerequisites

- Python 3.12+
- Poetry
- Docker (PostgreSQL + PostGIS)

## Quickstart

```bash
# Install dependencies
poetry install

# Create local env
cp .env.example .env

# Start PostgreSQL + Redis
docker-compose up -d

# Run migrations
poetry run alembic upgrade head

# Start API server
poetry run uvicorn canpoli.main:app --reload
```

## Common Commands

If you have GNU Make installed, these wrappers are available:

```bash
make setup
make dev
make test
make lint
make format
make typecheck
make migrate
make ingest
make ingest-parliament
make ingest-boundaries GEOJSON=/path/to/boundaries.geojson
```

## Testing

Unit tests (SQLite in-memory):

```bash
poetry run pytest
```

PostGIS integration tests:

```bash
POSTGIS_TEST_DATABASE_URL=postgresql+asyncpg://canpoli:canpoli_dev@localhost:5433/canpoli_test \
  poetry run pytest -m integration
```

## Linting and Formatting

```bash
poetry run ruff check .
poetry run ruff format .
```

## Type Checking

```bash
poetry run mypy canpoli
```

## Data Ingestion

See `docs/ingestion.md` for details on what each ingestion command does and when to run them.

## Pre-commit Hooks

```bash
poetry run pre-commit install
```
