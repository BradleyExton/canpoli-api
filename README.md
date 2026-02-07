# CanPoli API

Canadian Political Data API - Federal MPs, Ridings, and Parties.

## Setup

### Prerequisites

- Python 3.12+
- Poetry
- Docker (for PostgreSQL + PostGIS)

### Installation

```bash
# Clone and enter directory
cd ~/projects/canpoli-api

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start PostgreSQL
docker-compose up -d

# Run database migrations
poetry run alembic upgrade head

# Ingest data from House of Commons
poetry run python -m canpoli.cli.ingest

# Ingest riding boundaries (GeoJSON) for lat/lng lookup
poetry run python -m canpoli.cli.ingest_boundaries --geojson /path/to/boundaries.geojson

# Start development server
poetry run uvicorn canpoli.main:app --reload
```

## API Endpoints

### Health
- `GET /health` - API and database status

### Representatives
- `GET /v1/representatives` - Paginated list of representatives
  - Query params: `province`, `party`, `limit`, `offset`
- `GET /v1/representatives/{hoc_id}` - Single representative by House of Commons ID
- `GET /v1/representatives/lookup` - Lookup by postal code or coordinates
  - Postal code lookup not yet implemented
  - Lat/lng lookup requires PostGIS and riding boundary ingestion

### Ridings
- `GET /v1/ridings` - Paginated list of ridings
  - Query params: `province`, `limit`, `offset`
- `GET /v1/ridings/{id}` - Single riding with current representative

### Parties
- `GET /v1/parties` - All political parties

## Development

```bash
# Run tests
poetry run pytest

# Run PostGIS integration tests (requires local PostGIS)
# These use POSTGIS_TEST_DATABASE_URL to target the PostGIS service.
POSTGIS_TEST_DATABASE_URL=postgresql+asyncpg://canpoli:canpoli_dev@localhost:5433/canpoli_test \
  poetry run pytest tests/test_postgis_lookup.py tests/test_boundaries_ingest.py

# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Type check
poetry run mypy canpoli
```

## Data Source

MP data is sourced from the [House of Commons Open Data API](https://www.ourcommons.ca/Members/en/search/XML).
